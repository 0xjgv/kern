#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# === Logging ===
debug() { ${VERBOSE:-false} && echo "[$(date '+%H:%M:%S')] [DEBUG] $1" >&2 || true; }
log() { echo "[$(date '+%H:%M:%S')] $1" >&2; }
die() { log "ERROR: $2"; exit "$1"; }

# === Security: Input Sanitization ===
# Escape awk gsub() metacharacters (& and \)
sanitize_for_awk() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/&/\\&/g'
}

# Validate hint - reject prompt injection patterns
validate_hint() {
  local hint="$1"
  if [[ ${#hint} -gt 500 ]]; then
    die 1 "HINT too long (max 500 chars)"
  fi
  if echo "$hint" | grep -qiE 'ignore.*(previous|all).*instructions|disregard.*above|</(system|user|data)>'; then
    die 1 "HINT contains suspicious pattern"
  fi
}

# Wrap content to mark as untrusted data
wrap_untrusted() {
  local escaped=$(printf '%s' "$2" | sed 's|</data>|<\\/data>|gi')
  printf '<data source="%s">\n%s\n</data>' "$1" "$escaped"
}

# === Git Utilities ===
git_project_id() { basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; }
git_branch_safe() { local b=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown"); echo "${b//\//-}"; }

# === Task Extraction ===
extract_tasks() {
  local spec_file="${1:-SPEC.md}"
  # Output format: LINE_NUM|STATUS|DESCRIPTION
  # STATUS: ~ for in-progress, space for pending
  grep -n '^[[:space:]]*- \[\(~\| \)\]' "$spec_file" 2>/dev/null | \
    sed 's/^\([0-9]*\):- \[\(.\)\] /\1|\2|/'
}

mark_spec_line() {
  local line_num="$1" status="$2" spec_file="${3:-SPEC.md}"
  # status: "~" for in-progress, "x" for complete
  local tmp="${spec_file}.tmp"
  awk -v n="$line_num" -v s="$status" \
    'NR==n{sub(/\[(~| )\]/,"["s"]")} 1' "$spec_file" > "$tmp" && mv "$tmp" "$spec_file"
}

# === Claude CLI ===
# Read-only stages (0, 1, 3) - pre-approve only safe tools via --allowedTools
# This avoids permission prompts while restricting access
cld_ro() {
  CLAUDE_CODE_TASK_LIST_ID="$(git_project_id)-$(git_branch_safe)" \
  CLAUDE_CODE_ENABLE_TASKS=true \
  claude --allowedTools "Read,Glob,Grep,LS,TaskGet,TaskList" "$@"
}

# Write stage (2) - needs full permissions for edits and bash
cld_rw() {
  CLAUDE_CODE_TASK_LIST_ID="$(git_project_id)-$(git_branch_safe)" \
  CLAUDE_CODE_ENABLE_TASKS=true \
  claude --dangerously-skip-permissions "$@"
}

# Legacy alias (deprecated - use cld_ro or cld_rw explicitly)
cldd() { claude --dangerously-skip-permissions "$@"; }

PROJECT_ID=$(git_project_id) BRANCH=$(git_branch_safe)
export CLAUDE_CODE_TASK_LIST_ID="kern-$PROJECT_ID-$BRANCH"
VERBOSE=false DRY_RUN=false HINT=""
PROMPTS="$SCRIPT_DIR/prompts"

while getopts "vnc:h-:" opt; do
  case "$opt" in
    v) VERBOSE=true ;; n) DRY_RUN=true ;;
    c) MAX_TASKS="$OPTARG" ;;
    h) die 1 "Usage: kern [-v] [-n] [-c COUNT] [--hint TEXT] [task_id]" ;;
    -) case "$OPTARG" in
         hint) HINT="${!OPTIND}"; validate_hint "$HINT"; shift ;; verbose) VERBOSE=true ;;
         dry-run) DRY_RUN=true ;; count) MAX_TASKS="${!OPTIND}"; shift ;;
         *) die 1 "Unknown: --$OPTARG" ;;
       esac ;;
  esac
done
shift $((OPTIND-1))
TASK_ID="${1:-}"  # Now optional
MAX_TASKS="${MAX_TASKS:-5}"  # Default 5 iterations

build_prompt() {
  local tpl="$1"
  local safe_task_id safe_hint safe_diff safe_commits

  safe_task_id="$(sanitize_for_awk "${TASK_ID:-}")"
  safe_hint="$(sanitize_for_awk "$(wrap_untrusted 'hint' "${HINT:-}")")"
  safe_diff="$(sanitize_for_awk "$(wrap_untrusted 'git-diff' "$(git diff --stat 2>/dev/null | head -30)")")"
  safe_commits="$(sanitize_for_awk "$(wrap_untrusted 'git-log' "$(git log -5 --format='[%h] %s' 2>&1 | head -80 || echo 'none')")")"

  TASK_ID="$safe_task_id" HINT="$safe_hint" DIFF="$safe_diff" \
  RECENT_COMMITS="$safe_commits" SPEC_FILE="${SPEC_FILE:-SPEC.md}" \
  awk '/^---$/ { if (++fm == 2) next } fm < 2 && fm > 0 { next }
       { gsub(/\{TASK_ID\}/, ENVIRON["TASK_ID"])
         gsub(/\{HINT\}/, ENVIRON["HINT"])
         gsub(/\{DIFF\}/, ENVIRON["DIFF"])
         gsub(/\{RECENT_COMMITS\}/, ENVIRON["RECENT_COMMITS"])
         gsub(/\{SPEC_FILE\}/, ENVIRON["SPEC_FILE"]); print }' "$tpl"
}

run_stage() {
  local num="$1" name="$2" default_model="${3:-opus}"
  local tpl=$(echo "$PROMPTS"/${num}_*.md)
  local model=$(awk '/^---$/{if(++c==2)exit} c==1&&/^model:/{print $NF}' "$tpl")
  local output

  log "Stage $num: $name"

  if $DRY_RUN; then
    log "[DRY-RUN] Would run: cld --model ${model:-$default_model}"
    return 0
  fi

  # Select CLI based on stage: read-only for 0,1,3; read-write for 2
  local cli_cmd="cld_ro"
  [[ "$num" -eq 2 ]] && cli_cmd="cld_rw"

  output=$(build_prompt "$tpl" | $cli_cmd --model "${model:-$default_model}" \
    $($VERBOSE && echo "--verbose") -p "$(cat -)" 2>&1) || return 1

  # Stage 1 outputs task_id it selected/created
  if [[ "$num" -eq 1 ]] && [[ "$output" =~ task_id=([0-9]+) ]]; then
    TASK_ID="${BASH_REMATCH[1]}"
    export TASK_ID
    debug "Stage 1 selected task: $TASK_ID"
    echo "$output"
  fi

  # Check for SUCCESS in output
  [[ "$output" =~ SUCCESS ]] || { echo "$output" >&2; return 1; }
}

run_stage_0() {
  local tpl="$PROMPTS/0_populate_queue.md"
  log "Stage 0: Populate Task Queue"

  if $DRY_RUN; then
    log "[DRY-RUN] Would populate task queue from SPEC.md"
    return 0
  fi

  SPEC_FILE="SPEC.md" build_prompt "$tpl" | cld_ro --model haiku \
    $($VERBOSE && echo "--verbose") -p "$(cat -)" || return 1
}

run_task() {
  log "Executing task: ${TASK_ID:-<pending>}"
  run_stage 1 "Research & Planning" opus || return 1
  # TASK_ID now set by Stage 1
  run_stage 2 "Implement" opus || return 1
  if ! git diff --quiet || ! git diff --cached --quiet; then
    run_stage 3 "Commit & Review" haiku || return 1
  else
    log "No changes to commit"
  fi
  log "Task $TASK_ID completed"
}

if [[ -n "$TASK_ID" ]]; then
  # Single task mode (backward compatible)
  run_task || die 1 "Task $TASK_ID failed"
else
  # Iteration mode: populate queue, then process tasks

  if $DRY_RUN; then
    # Show what would be processed without looping
    log "[DRY-RUN] Would process up to $MAX_TASKS tasks from SPEC.md:"
    extract_tasks SPEC.md | head -n "$MAX_TASKS" | while IFS='|' read -r line status desc; do
      log "  - Line $line: $desc"
    done
    exit 0
  fi

  # Stage 0: Populate task queue from SPEC.md (idempotent)
  run_stage_0 || die 1 "Failed to populate task queue"

  # Process tasks from queue
  task_count=0
  while true; do
    # Check max tasks limit
    if [[ "$task_count" -ge "$MAX_TASKS" ]]; then
      log "Reached max tasks limit ($MAX_TASKS)"
      break
    fi

    # Clear TASK_ID so Stage 1 selects from queue
    unset TASK_ID

    # Run the pipeline (Stage 1 selects task and sets TASK_ID)
    if ! run_task; then
      # Stage 1 returns failure when no more tasks
      if [[ -z "$TASK_ID" ]]; then
        break  # No more tasks in queue
      fi
      die 1 "Task $TASK_ID failed"
    fi

    ((task_count++))
  done

  if [[ "$task_count" -eq 0 ]]; then
    log "No pending tasks in queue"
  else
    log "Completed $task_count task(s)"
  fi
fi
