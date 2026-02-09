#!/bin/bash
set -eo pipefail
VERSION="0.1.0-dev"

# Resolve symlinks to find actual script location (portable for macOS/Linux)
SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SOURCE" ]]; do
  DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"

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

# Legacy alias (deprecated - use cld_ro or cld_rw explicitly)
export CLAUDE_CODE_TASK_LIST_ID="kern-$(git_project_id)-$(git_branch_safe)"
cldd() { claude --dangerously-skip-permissions "$@"; }
export CLAUDE_CODE_ENABLE_TASKS=true

# === Claude CLI ===
# Stage-specific tool restrictions via --allowedTools
# Stage 0: Read + Task tools (create/update tasks from SPEC.md)
cld_s0() {
  cldd "$@"
}

# Stage 1: Read + Task tools + Task agent (for research subagents)
cld_s1() {
  cldd "$@"
}

# Stage 3: Read + Task tools + Bash (for git commit)
cld_s3() {
  cldd "$@"
}

# Legacy read-only alias (deprecated - use stage-specific functions)
cld_ro() {
  cldd "$@"
}

# Write stage (2) - needs full permissions for edits and bash
cld_rw() {
  cldd "$@"
}


VERBOSE=false DRY_RUN=false HINT=""
PROMPTS="$SCRIPT_DIR/prompts"

# Handle special flags before getopts
case "${1:-}" in
  -V|--version) echo "kern $VERSION"; exit 0 ;;
  --update) curl -fsSL https://raw.githubusercontent.com/0xjgv/kern/main/install.sh | bash; exit $? ;;
  -h|--help) echo "Usage: kern [-v] [-n] [-c COUNT] [--hint TEXT] [task_id]"; exit 0 ;;
esac

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

  # Select CLI based on stage number
  local cli_cmd
  case "$num" in
    0) cli_cmd="cld_s0" ;;
    1) cli_cmd="cld_s1" ;;
    2) cli_cmd="cld_rw" ;;
    3) cli_cmd="cld_s3" ;;
    *) cli_cmd="cld_ro" ;;
  esac

  output=$(build_prompt "$tpl" | $cli_cmd --model "${model:-$default_model}" \
    $($VERBOSE && echo "--verbose") -p "$(cat -)" 2>&1) || return 1

  # Stage 1 outputs task_id it selected/created
  if [[ "$num" -eq 1 ]] && [[ "$output" =~ task_id=([0-9]+) ]]; then
    TASK_ID="${BASH_REMATCH[1]}"
    export TASK_ID
    debug "Stage 1 selected task: $TASK_ID"

    # Check for skip signal (task already complete)
    if [[ "$output" =~ skip=true ]]; then
      SKIP_TASK=true
      export SKIP_TASK
      debug "Task $TASK_ID already complete, will skip"
    fi

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

  SPEC_FILE="SPEC.md" build_prompt "$tpl" | cld_s0 --model haiku \
    $($VERBOSE && echo "--verbose") -p "$(cat -)" || return 1
}

run_task() {
  SKIP_TASK=false  # Reset for each task
  [[ -z "$TASK_ID" ]] && log "Selecting next task..."
  run_stage 1 "Research & Planning" opus || return 1

  # Check if Stage 1 found a task (task_id=none means queue empty)
  if [[ -z "$TASK_ID" ]]; then
    log "No more tasks in queue"
    return 1
  fi

  log "Executing task: $TASK_ID"

  # Short-circuit if task already complete
  if $SKIP_TASK; then
    log "Task $TASK_ID already complete, skipping implementation"
    return 0
  fi

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
