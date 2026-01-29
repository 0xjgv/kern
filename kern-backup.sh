#!/bin/bash
set -e

# === Version (injected from git tag during release) ===
VERSION="dev"
REPO="0xjgv/kern"

# Handle --version and --update before anything else
if [[ "${1:-}" == "--version" || "${1:-}" == "-V" ]]; then
  echo "kern $VERSION"
  exit 0
fi

if [[ "${1:-}" == "--update" ]]; then
  echo "Updating kern..."
  curl -fsSL "https://raw.githubusercontent.com/$REPO/main/install.sh" | sh
  exit $?
fi

# === Configuration ===
# Resolve symlinks to find actual script location
SCRIPT_PATH="${BASH_SOURCE[0]}"
while [[ -L "$SCRIPT_PATH" ]]; do
  SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
  SCRIPT_PATH="$(readlink "$SCRIPT_PATH")"
  [[ "$SCRIPT_PATH" != /* ]] && SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_PATH"
done
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
SPEC="./SPEC.md"
LEARNINGS="./LEARNINGS.md"
PROMPTS="$SCRIPT_DIR/prompts"

# Project+branch scoped directories (prevent collisions between repos/worktrees)
PROJECT_ID=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
OUTPUT_DIR="/tmp/claude/kern/$PROJECT_ID/$BRANCH"
# Unified task list ID for Claude Code's native task persistence
export CLAUDE_CODE_TASK_LIST_ID="kern-$PROJECT_ID-${BRANCH//\//-}"
# State derived from SPEC.md + stage files (no state file needed)
LOCKDIR="/tmp/claude/kern/$PROJECT_ID-${BRANCH//\//-}.lock.d"
PIDFILE="$LOCKDIR/pid"

# === Defaults ===
VERBOSE=false
DRY_RUN=false
TASK_ID=""
HINT=""

# === Exit Codes ===
EXIT_SUCCESS=0
EXIT_STAGE_FAILED=1
EXIT_TASK_NOT_FOUND=2
EXIT_LOCK_CONFLICT=3

# === Usage ===
usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS] <task_id>

Execute a single task through the 3-stage pipeline.

Options:
  --hint "..."   Guidance from CC (injected into prompts)
  -v, --verbose  Enable verbose logging
  -n, --dry-run  Show what would be done
  -V, --version  Show version
  --update       Update to latest version
  -h, --help     Show this help message

Arguments:
  task_id        ID of task to execute (required)

Exit codes:
  0 = SUCCESS (all stages completed, committed)
  1 = STAGE_FAILED
  2 = TASK_NOT_FOUND
  3 = LOCK_CONFLICT

Examples:
  kern 123               # Execute task 123
  kern --hint "Try X" 5  # Execute task 5 with hint
  kern -v 42             # Verbose mode, task 42
  kern -n 7              # Dry run task 7
EOF
  exit 0
}

# === Parse Arguments ===
while [[ $# -gt 0 ]]; do
  case "$1" in
    --hint)
      HINT="$2"
      shift 2
      ;;
    -v|--verbose)
      VERBOSE=true
      shift
      ;;
    -n|--dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      ;;
    -*)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
    *)
      TASK_ID="$1"
      shift
      ;;
  esac
done

# Validate task_id is provided
if [[ -z "$TASK_ID" ]]; then
  echo "Error: task_id required" >&2
  usage
fi

# === Helpers ===
cleanup() {
  rm -f "$PIDFILE" 2>/dev/null || true
  rmdir "$LOCKDIR" 2>/dev/null || true
}
trap cleanup EXIT

log() { echo "[$(date '+%H:%M:%S')] $1" >&2; }
debug() { ! $VERBOSE || echo "[$(date '+%H:%M:%S')] [DEBUG] $1" >&2; }
stage_file() { echo "$OUTPUT_DIR/stage${1}.json"; }
task_dir() { echo "$HOME/.claude/tasks/$CLAUDE_CODE_TASK_LIST_ID"; }
show_result() { jq -r '.result // ""' "$1" 2>/dev/null; }
stage_failed() { jq -e '.is_error == true' "$(stage_file "$1")" >/dev/null 2>&1; }

# Extract embedded JSON from stage result (agent outputs JSON in markdown code block)
extract_stage_json() {
  local stage_file="$1" field="$2" default="${3:-}"
  local result=$(jq -r '.result // ""' "$stage_file" 2>/dev/null)
  local json=$(echo "$result" | sed -n '/```json/,/```/p' | sed '1d;$d')
  [[ -n "$json" ]] && echo "$json" | jq -r "$field // \"$default\"" 2>/dev/null || echo "$default"
}

# Check if lock is stale (process no longer running)
check_stale_lock() {
  [[ -d "$LOCKDIR" ]] || return 0
  local old_pid=$(cat "$PIDFILE" 2>/dev/null || echo "")
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    return 1  # Lock is active
  fi
  [[ -n "$old_pid" ]] && log "Removing stale lock from PID $old_pid" || log "Removing orphaned lock directory"
  rm -rf "$LOCKDIR"
}

# Extract current task from queue (for context injection into prompts)
extract_task() {
  local task_file
  task_file=$(find_task_by_status "in_progress") || return 0
  jq -r '"Task ID: \(.id)\n- [~] \(.subject)\n  > \(.description // "")"' "$task_file" 2>/dev/null
}

# Find first task file matching a status; prints path if found
find_task_by_status() {
  local target_status="$1" dir=$(task_dir)
  [[ -d "$dir" ]] || return 1
  local f
  for f in "$dir"/*.json; do
    [[ -f "$f" ]] || continue
    [[ "$(jq -r '.status // ""' "$f" 2>/dev/null)" == "$target_status" ]] && { echo "$f"; return 0; }
  done
  return 1
}

# Get status of a specific task by ID
get_task_status() {
  local f="$(task_dir)/$1.json"
  [[ -f "$f" ]] && jq -r '.status // ""' "$f" 2>/dev/null
}

# Validate task exists before starting; prints task file path
validate_task() {
  local f="$(task_dir)/$1.json"
  [[ -f "$f" ]] && { echo "$f"; return 0; }
  log "ERROR: Task $1 not found"
  exit $EXIT_TASK_NOT_FOUND
}

# Write structured error JSON on failure
write_error_json() {
  local stage="$1" error="$2"
  local output="$OUTPUT_DIR/error.json"
  cat > "$output" <<EOF
{
  "stage": $stage,
  "task_id": "$TASK_ID",
  "error": "$error",
  "details": "See stage${stage}.json and stage${stage}.log for details"
}
EOF
}

# Display task state with full metadata
display_task() {
  local task_file="$1"
  [[ -f "$task_file" ]] || return 1

  local status=$(jq -r '.status // "unknown"' "$task_file")
  local indicator="○"
  case "$status" in
    pending)     indicator="○" ;;
    in_progress) indicator="◐" ;;
    completed)   indicator="●" ;;
  esac

  echo "┌─────────────────────────────────────────────────────────────"
  jq -r --arg i "$indicator" \
    '"│ \($i) Task #\(.id): \(.subject)\n│ Status: \(.status) | Active: \(.activeForm // "—")"' \
    "$task_file" 2>/dev/null

  # Show all metadata fields
  local meta=$(jq -r '.metadata // {} | to_entries[] | "│   \(.key): \(.value | if type == "array" then join(", ") elif type == "object" then tostring else . end)"' "$task_file" 2>/dev/null)
  [[ -n "$meta" ]] && echo "│ Metadata:" && echo "$meta"
  echo "└─────────────────────────────────────────────────────────────"
}

# Start background watcher that displays task updates
# Returns watcher PID via stdout
start_task_watcher() {
  local task_file="$1"
  local interval="${2:-2}"  # Check every 2 seconds

  (
    local last_hash=""
    while true; do
      if [[ -f "$task_file" ]]; then
        local hash=$(md5 -q "$task_file" 2>/dev/null || md5sum "$task_file" 2>/dev/null | cut -d' ' -f1)
        if [[ "$hash" != "$last_hash" ]]; then
          last_hash="$hash"
          echo ""  # New line before update
          display_task "$task_file"
        fi
      fi
      sleep "$interval"
    done
  ) &
  echo $!
}

# Stop watcher process
stop_task_watcher() {
  local pid="$1"
  [[ -n "$pid" ]] && kill "$pid" 2>/dev/null
  return 0
}

# Build prompt with context substitution (strips frontmatter)
build_prompt() {
  local template="$1"
  local prev_result_file="${2:-}"

  # Gather context directly into variables
  local commits learnings task diff prev_result task_id hint
  commits=$(git log -5 --format="[%h] %s" --stat 2>&1 | head -80) || commits="No commits yet"
  learnings=$(cat "$LEARNINGS" 2>/dev/null) || learnings="No learnings yet."
  task=$(extract_task)
  diff=$(git diff --stat 2>&1 | head -50) || diff="No changes"
  [[ -n "$prev_result_file" && -f "$prev_result_file" ]] && prev_result=$(show_result "$prev_result_file") || prev_result=""
  task_id="${CURRENT_TASK_ID:-$TASK_ID}"
  hint="${HINT:-}"

  # Extract structured fields from stage1.json if it exists (for stage 2)
  # Note: Claude CLI wraps output; embedded JSON is in .result as markdown code block
  local stage1_files="" stage1_pattern="" stage1_constraints="" stage1_plan=""
  local stage1=$(stage_file 1)
  if [[ -f "$stage1" ]]; then
    stage1_files=$(extract_stage_json "$stage1" '.research.files | join(", ")' "")
    stage1_pattern=$(extract_stage_json "$stage1" '.research.pattern' "")
    stage1_constraints=$(extract_stage_json "$stage1" '.research.constraints | join(", ")' "")
    stage1_plan=$(extract_stage_json "$stage1" '.plan | to_entries | map("  \(.key + 1). \(.value)") | join("\n")' "")
  fi

  # Extract structured fields from stage2.json if it exists (for stage 3)
  local stage2_files="" stage2_added="" stage2_removed="" stage2_validation=""
  local stage2=$(stage_file 2)
  if [[ -f "$stage2" ]]; then
    stage2_files=$(extract_stage_json "$stage2" '.files_changed | join(", ")' "")
    stage2_added=$(extract_stage_json "$stage2" '.lines_added' "0")
    stage2_removed=$(extract_stage_json "$stage2" '.lines_removed' "0")
    stage2_validation=$(extract_stage_json "$stage2" '.validation' "")
  fi

  # awk substitution (ENVIRON avoids escaping issues with -v)
  COMMITS="$commits" LEARNINGS="$learnings" TASK="$task" DIFF="$diff" \
  PREV_RESULT="$prev_result" TASK_ID="$task_id" HINT="$hint" \
  STAGE1_FILES="$stage1_files" STAGE1_PATTERN="$stage1_pattern" \
  STAGE1_CONSTRAINTS="$stage1_constraints" STAGE1_PLAN="$stage1_plan" \
  STAGE2_FILES="$stage2_files" STAGE2_ADDED="$stage2_added" \
  STAGE2_REMOVED="$stage2_removed" STAGE2_VALIDATION="$stage2_validation" \
    awk '
      /^---$/ { if (++fm == 2) next }
      fm < 2 && fm > 0 { next }
      {
        gsub(/\{COMMITS\}/, ENVIRON["COMMITS"])
        gsub(/\{LEARNINGS\}/, ENVIRON["LEARNINGS"])
        gsub(/\{TASK\}/, ENVIRON["TASK"])
        gsub(/\{DIFF\}/, ENVIRON["DIFF"])
        gsub(/\{PREV_RESULT\}/, ENVIRON["PREV_RESULT"])
        gsub(/\{TASK_ID\}/, ENVIRON["TASK_ID"])
        gsub(/\{HINT\}/, ENVIRON["HINT"])
        gsub(/\{STAGE1_FILES\}/, ENVIRON["STAGE1_FILES"])
        gsub(/\{STAGE1_PATTERN\}/, ENVIRON["STAGE1_PATTERN"])
        gsub(/\{STAGE1_CONSTRAINTS\}/, ENVIRON["STAGE1_CONSTRAINTS"])
        gsub(/\{STAGE1_PLAN\}/, ENVIRON["STAGE1_PLAN"])
        gsub(/\{STAGE2_FILES\}/, ENVIRON["STAGE2_FILES"])
        gsub(/\{STAGE2_ADDED\}/, ENVIRON["STAGE2_ADDED"])
        gsub(/\{STAGE2_REMOVED\}/, ENVIRON["STAGE2_REMOVED"])
        gsub(/\{STAGE2_VALIDATION\}/, ENVIRON["STAGE2_VALIDATION"])
        print
      }
    ' "$template"
}

# Run Claude with retry logic
run_claude() {
  local stage_name="$1"
  local prompt_file="$2"
  local output_file="$3"
  local model="${4:-opus}"
  local max_retries=3
  local retry_delay=5
  local log_file="${output_file%.json}.log"

  for attempt in $(seq 1 $max_retries); do
    debug "Attempt $attempt/$max_retries for $stage_name (model=$model)"

    local agents_file="$SCRIPT_DIR/agents.json"
    local cmd_args=(
      claude
      --dangerously-skip-permissions
      -p "$(cat "$prompt_file")"
      --output-format json
      --model "$model"
      --debug-file "$log_file"
    )
    [[ -f "$agents_file" ]] && cmd_args+=(--agents "$(cat "$agents_file")")

    if $DRY_RUN; then
      log "[DRY-RUN] Would run: ${cmd_args[*]:0:5}... > $output_file"
      echo '{"result": "DRY_RUN", "usage": {"input_tokens": 0, "output_tokens": 0}}' > "$output_file"
      return 0
    fi

    local exit_code=0
    CLAUDE_CODE_ENABLE_TASKS=true \
    CLAUDE_CODE_TASK_LIST_ID="kern-$PROJECT_ID-$BRANCH" \
      "${cmd_args[@]}" > "$output_file" 2>&1 || exit_code=$?

    # Check if output is valid JSON
    if jq empty "$output_file" 2>/dev/null; then
      return 0
    fi

    # Check for transient errors (API errors, timeouts)
    if [[ $exit_code -ne 0 ]]; then
      log "Attempt $attempt failed (exit code: $exit_code)"
      if [[ $attempt -lt $max_retries ]]; then
        local sleep_time=$((retry_delay * attempt))
        log "Retrying in ${sleep_time}s..."
        sleep $sleep_time
      fi
    else
      # Exit code 0 but invalid JSON
      log "WARNING: Invalid JSON output from $stage_name"
      return 1
    fi
  done

  log "ERROR: $stage_name failed after $max_retries attempts"
  return 1
}

# Run a stage with temp file management
run_stage() {
  local name="$1" template="$2" output="$3"
  local prev_output="${4:-}"  # Optional: previous stage output file

  # Parse model from frontmatter (inline - used only here)
  local model=$(awk '/^---$/{if(++c==2)exit} c==1&&$1=="model:"{gsub(/^[^:]+: */,"");print;exit}' "$template")
  debug "Stage $name: model=${model:-sonnet}"

  local prompt_file=$(mktemp)
  trap "rm -f '$prompt_file'" RETURN
  build_prompt "$template" "$prev_output" > "$prompt_file"
  run_claude "$name" "$prompt_file" "$output" "${model:-sonnet}"
}

# Execute a stage with consistent logging/error handling
# Usage: execute_stage <num> <label> <name> [prev_num] [exit_on_fail]
# - num: stage number (0-3)
# - label: display label for logging (e.g., "Sync Task Queue")
# - name: template name without number prefix (e.g., "generate")
# - prev_num: previous stage number for context (optional)
# - exit_on_fail: "true" to exit on failure (default: false)
execute_stage() {
  local num="$1" label="$2" name="$3"
  local prev_num="${4:-}" exit_on_fail="${5:-false}"
  local output=$(stage_file "$num")
  local prev_output=""
  [[ -n "$prev_num" ]] && prev_output=$(stage_file "$prev_num")

  log "Stage $num: $label"

  # Start task watcher if we have a task in progress (skip in dry-run)
  local watcher_pid=""
  local task_file=$(find_task_by_status "in_progress" 2>/dev/null)
  if [[ -n "$task_file" ]]; then
    display_task "$task_file"
    $DRY_RUN || watcher_pid=$(start_task_watcher "$task_file")
  fi

  # Run the stage
  local stage_result=0
  if ! run_stage "$name" "$PROMPTS/${num}_${name}.md" "$output" "$prev_output"; then
    log "Stage $num failed"
    stage_result=1
  fi

  # Stop watcher and show final state
  stop_task_watcher "$watcher_pid"
  [[ -n "$task_file" && -f "$task_file" ]] && display_task "$task_file"

  show_result "$output"
  [[ $stage_result -eq 0 ]] || { $exit_on_fail && exit 1; return 1; }
}

# === Main ===

# Check for stale lock before attempting to acquire
check_stale_lock

# Ensure parent directory exists before lock acquisition
mkdir -p "$(dirname "$LOCKDIR")"

# Prevent concurrent runs (mkdir is atomic)
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  log "Already running (PID: $(cat "$PIDFILE" 2>/dev/null || echo "unknown"))"
  exit $EXIT_LOCK_CONFLICT
fi

# Write our PID for stale lock detection
echo $$ > "$PIDFILE"

# Keep system awake while script runs (macOS only, auto-terminates with shell)
caffeinate -im -w $$ 2>/dev/null &

# Create output directory
mkdir -p "$OUTPUT_DIR"

# === Validate Required Files ===
if [[ ! -f "$SPEC" ]]; then
  log "ERROR: $SPEC not found"
  log "Create a SPEC.md with tasks (any checkbox format works)"
  exit 1
fi

for prompt in 1_research 2_implement 3_commit; do
  if [[ ! -f "$PROMPTS/${prompt}.md" ]]; then
    log "ERROR: Missing prompt template: $PROMPTS/${prompt}.md"
    exit 1
  fi
done

# Show configuration
log "Executing task: $TASK_ID"
! $VERBOSE || log "Verbose mode enabled"
! $DRY_RUN || log "Dry-run mode - no changes will be made"

# Validate task exists
task_file=$(validate_task "$TASK_ID")
display_task "$task_file"

# Export for prompts
export CURRENT_TASK_ID="$TASK_ID"

# === Stage 1: Research + Plan ===
if ! execute_stage 1 "Research" "research" || stage_failed 1; then
  write_error_json 1 "Research stage failed"
  exit $EXIT_STAGE_FAILED
fi

# === Stage 2: Implement ===
if ! execute_stage 2 "Implement" "implement" 1 || stage_failed 2; then
  write_error_json 2 "Implementation stage failed"
  exit $EXIT_STAGE_FAILED
fi

# === Stage 3: Commit ===
# Only run if there are changes to commit
if git diff --quiet && git diff --cached --quiet; then
  log "No changes to commit"
  # Still success - task may have been a no-op
  echo '{"status": "SUCCESS", "task_id": "'"$TASK_ID"'", "commit": null, "message": "No changes needed"}' > "$(stage_file 3)"
  exit $EXIT_SUCCESS
fi

log "Stage 3: Commit"
if ! execute_stage 3 "Commit" "commit" 2; then
  write_error_json 3 "Commit stage failed"
  exit $EXIT_STAGE_FAILED
fi

# Show commit result
commit_hash=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
log "Task $TASK_ID completed successfully (commit: $commit_hash)"
exit $EXIT_SUCCESS
