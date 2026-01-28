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
MAX_ITER=5
DELAY=10

# === Usage ===
usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS] [MAX_ITER] [DELAY]

Autonomous development pipeline - 3-stage task execution.

Options:
  -v, --verbose    Enable verbose logging
  -n, --dry-run    Show what would be done without executing
  -V, --version    Show version
  --update         Update to latest version
  -h, --help       Show this help message

Arguments:
  MAX_ITER         Maximum iterations (default: 5)
  DELAY            Delay between iterations in seconds (default: 10)

Examples:
  kern                 # Run 5 iterations
  kern 10 30           # Run 10 iterations, 30s delay
  kern -v 5            # Verbose mode, 5 iterations
  kern -n              # Dry run to see what would happen
  kern --version       # Show version
  kern --update        # Update to latest version
EOF
  exit 0
}

# === Parse Arguments ===
while [[ $# -gt 0 ]]; do
  case "$1" in
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
      usage
      ;;
    *)
      if [[ -z "${MAX_ITER_SET:-}" ]]; then
        MAX_ITER="$1"
        MAX_ITER_SET=true
      else
        DELAY="$1"
      fi
      shift
      ;;
  esac
done

# === Helpers ===
cleanup() {
  rm -f "$PIDFILE" 2>/dev/null || true
  rmdir "$LOCKDIR" 2>/dev/null || true
}
trap cleanup EXIT

log() { echo "[$(date '+%H:%M:%S')] $1" >&2; }
debug() { ! $VERBOSE || echo "[$(date '+%H:%M:%S')] [DEBUG] $1" >&2; }
show_result() { jq -r '.result // ""' "$1" 2>/dev/null; }

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
  local target_status="$1"
  local task_dir="$HOME/.claude/tasks/$CLAUDE_CODE_TASK_LIST_ID"
  [[ -d "$task_dir" ]] || return 1
  local task_file
  for task_file in "$task_dir"/*.json; do
    [[ -f "$task_file" ]] || continue
    [[ "$(jq -r '.status // ""' "$task_file" 2>/dev/null)" == "$target_status" ]] && { echo "$task_file"; return 0; }
  done
  return 1
}

# Check if task queue has work (pending or in-progress)
has_queued_work() {
  find_task_by_status "pending" >/dev/null || find_task_by_status "in_progress" >/dev/null
}


# Build prompt with context substitution (strips frontmatter)
build_prompt() {
  local template="$1"
  local prev_result_file="${2:-}"

  # Gather context directly into variables
  local commits learnings task diff prev_result
  commits=$(git log -5 --format="[%h] %s" --stat 2>&1 | head -80) || commits="No commits yet"
  learnings=$(cat "$LEARNINGS" 2>/dev/null) || learnings="No learnings yet."
  task=$(extract_task)
  diff=$(git diff --stat 2>&1 | head -50) || diff="No changes"
  [[ -n "$prev_result_file" && -f "$prev_result_file" ]] && prev_result=$(jq -r '.result // ""' "$prev_result_file") || prev_result=""

  # awk substitution (ENVIRON avoids escaping issues with -v)
  COMMITS="$commits" LEARNINGS="$learnings" TASK="$task" DIFF="$diff" PREV_RESULT="$prev_result" \
    awk '
      /^---$/ { if (++fm == 2) next }
      fm < 2 && fm > 0 { next }
      { gsub(/\{COMMITS\}/, ENVIRON["COMMITS"]); gsub(/\{LEARNINGS\}/, ENVIRON["LEARNINGS"]); gsub(/\{TASK\}/, ENVIRON["TASK"]); gsub(/\{DIFF\}/, ENVIRON["DIFF"]); gsub(/\{PREV_RESULT\}/, ENVIRON["PREV_RESULT"]); print }
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


# Check if a stage output file is valid (exists and has .result field)
stage_complete() {
  local stage_file="$1"
  [[ -f "$stage_file" ]] && jq -e '.result' "$stage_file" >/dev/null 2>&1
}

# Detect where to resume based on task queue + stage files
# Sets RESUME_FROM to: 1 (research), 2 (implement), or 3 (commit)
detect_resume_stage() {
  RESUME_FROM=1
  find_task_by_status "in_progress" >/dev/null || return 0
  stage_complete "$OUTPUT_DIR/stage2.json" && RESUME_FROM=3 && return 0
  stage_complete "$OUTPUT_DIR/stage1.json" && RESUME_FROM=2
}

# === Main ===

# Check for stale lock before attempting to acquire
check_stale_lock

# Ensure parent directory exists before lock acquisition
mkdir -p "$(dirname "$LOCKDIR")"

# Prevent concurrent runs (mkdir is atomic)
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  log "Already running (PID: $(cat "$PIDFILE" 2>/dev/null || echo "unknown"))"
  exit 1
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

for prompt in 0_generate 1_research 2_implement 3_commit; do
  if [[ ! -f "$PROMPTS/${prompt}.md" ]]; then
    log "ERROR: Missing prompt template: $PROMPTS/${prompt}.md"
    exit 1
  fi
done

# Show configuration
log "Configuration: max_iter=$MAX_ITER delay=${DELAY}s"
! $VERBOSE || log "Verbose mode enabled"
! $DRY_RUN || log "Dry-run mode - no changes will be made"

# Detect resume state from SPEC.md + stage files
detect_resume_stage
[[ $RESUME_FROM -gt 1 ]] && log "Resuming from stage: $RESUME_FROM"

for i in $(seq 1 $MAX_ITER); do
  log "=== Iteration $i/$MAX_ITER ==="

  # === Stage 0: Sync Task Queue ===
  log "Stage 0: Sync Task Queue"
  if ! run_stage "generate" "$PROMPTS/0_generate.md" "$OUTPUT_DIR/stage0.json"; then
    log "Stage 0 failed"
    exit 1
  fi
  show_result "$OUTPUT_DIR/stage0.json"

  # === Stage 1: Research ===
  if [[ $RESUME_FROM -gt 1 ]]; then
    log "Stage 1: Skipped (resuming)"
  else
    log "Stage 1: Select and Research"

    if ! run_stage "research" "$PROMPTS/1_research.md" "$OUTPUT_DIR/stage1.json"; then
      log "Stage 1 failed"
      exit 1
    fi
    show_result "$OUTPUT_DIR/stage1.json"

    # Validate JSON output
    stage_complete "$OUTPUT_DIR/stage1.json" || log "WARNING: Stage 1 output missing 'result' field"

    # Check if no task available
    if jq -r '.result // ""' "$OUTPUT_DIR/stage1.json" | grep -q "NO_TASK"; then
      log "No task available"
      exit 0
    fi

    # Verify a task was selected (check queue, not SPEC.md)
    if ! find_task_by_status "in_progress" >/dev/null; then
      log "No task marked in-progress after Stage 1"
      exit 1
    fi
  fi

  # === Stage 2: Implement ===
  if [[ $RESUME_FROM -gt 2 ]]; then
    log "Stage 2: Skipped (resuming)"
  else
    log "Stage 2: Plan and Implement"

    if ! run_stage "implement" "$PROMPTS/2_implement.md" "$OUTPUT_DIR/stage2.json" "$OUTPUT_DIR/stage1.json"; then
      log "Stage 2 failed"
      # Continue to check for partial changes
    fi
    show_result "$OUTPUT_DIR/stage2.json"
  fi

  # Validate JSON and extract result
  if ! stage_complete "$OUTPUT_DIR/stage2.json"; then
    log "WARNING: Stage 2 output missing 'result' field"
    result=""
  else
    result=$(jq -r '.result // ""' "$OUTPUT_DIR/stage2.json" | tail -1)
  fi

  case "$result" in
    *SUCCESS*)
      log "Implementation succeeded"
      ;;
    *DECOMPOSED*)
      log "Task decomposed into subtasks, continuing to next iteration"
      [ $i -lt $MAX_ITER ] && sleep $DELAY
      continue
      ;;
    *SKIPPED*)
      log "Task skipped, continuing to next iteration"
      [ $i -lt $MAX_ITER ] && sleep $DELAY
      continue
      ;;
    *)
      log "Implementation did not succeed (result: $result)"
      log "Check $OUTPUT_DIR/stage2.json for details"
      # Continue anyway to see if there are uncommitted changes worth committing
      ;;
  esac

  # === Stage 3: Commit ===
  # Only run if there are changes to commit
  if git diff --quiet && git diff --cached --quiet; then
    log "No changes to commit"
    [ $i -lt $MAX_ITER ] && sleep $DELAY
    continue
  fi

  log "Stage 3: Review and Commit"

  if ! run_stage "commit" "$PROMPTS/3_commit.md" "$OUTPUT_DIR/stage3.json" "$OUTPUT_DIR/stage2.json"; then
    log "Stage 3 failed"
    # Don't exit - changes are still there for manual commit
  fi
  show_result "$OUTPUT_DIR/stage3.json"

  # Show commit result
  commit_hash=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
  log "Committed: $commit_hash"

  # Clear resume state after first iteration completes
  RESUME_FROM=1

  # Clean up stage files for next iteration
  rm -f "$OUTPUT_DIR"/stage*.json

  [ $i -lt $MAX_ITER ] && sleep $DELAY
done

# Final summary
log "Max iterations reached"
