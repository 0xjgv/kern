#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/functions.sh"

PROJECT_ID=$(git_project_id) BRANCH=$(git_branch_safe)
OUTPUT_DIR="/tmp/claude/kern/$PROJECT_ID/$BRANCH"
export CLAUDE_CODE_TASK_LIST_ID="kern-$PROJECT_ID-$BRANCH"
PROMPTS="$SCRIPT_DIR/prompts" LEARNINGS="./LEARNINGS.md"
VERBOSE=false DRY_RUN=false HINT=""

while getopts "vnh:-:" opt; do
  case "$opt" in
    v) VERBOSE=true ;; n) DRY_RUN=true ;;
    h) die 1 "Usage: kern [-v] [-n] [--hint TEXT] <task_id>" ;;
    -) case "$OPTARG" in
         hint) HINT="${!OPTIND}"; shift ;; verbose) VERBOSE=true ;;
         dry-run) DRY_RUN=true ;; *) die 1 "Unknown: --$OPTARG" ;;
       esac ;;
  esac
done
shift $((OPTIND-1))
TASK_ID="${1:?Error: task_id required}"

stage_file() { echo "$OUTPUT_DIR/stage${1}.json"; }

build_prompt() {
  COMMITS=$(git log -5 --format="[%h] %s" 2>/dev/null | head -20)
  LEARNINGS=$(cat "$LEARNINGS" 2>/dev/null || echo "")
  DIFF=$(git diff --stat 2>/dev/null | head -30)
  COMMITS="$COMMITS" LEARNINGS="$LEARNINGS" DIFF="$DIFF" \
  TASK_ID="$TASK_ID" HINT="$HINT" awk '
    /^---$/ { if (++fm == 2) next } fm < 2 && fm > 0 { next }
    { gsub(/\{COMMITS\}/, ENVIRON["COMMITS"]); gsub(/\{LEARNINGS\}/, ENVIRON["LEARNINGS"])
      gsub(/\{DIFF\}/, ENVIRON["DIFF"]); gsub(/\{TASK_ID\}/, ENVIRON["TASK_ID"])
      gsub(/\{HINT\}/, ENVIRON["HINT"]); print }' "$1"
}

run_claude() {
  local name="$1" out="$2" model="${3:-sonnet}"
  debug "Running $name (model=$model)"
  if $DRY_RUN; then
    log "[DRY-RUN] Would run: claude --model $model > $out"
    echo '{"result":"DRY_RUN","is_error":false}' > "$out"; return 0
  fi
  CLAUDE_CODE_ENABLE_TASKS=true claude --dangerously-skip-permissions \
    --output-format json --model "$model" -p "$(cat -)" > "$out" 2>&1
  jq -e '.is_error != true' "$out" >/dev/null
}

run_stage() {
  local num="$1" name="$2" default_model="${3:-opus}"
  local tpl=$(echo "$PROMPTS"/${num}_*.md)
  local model=$(awk '/^---$/{if(++c==2)exit} c==1&&/^model:/{print $NF}' "$tpl")
  log "Stage $num: $name"
  build_prompt "$tpl" | run_claude "$name" "$(stage_file $num)" "${model:-$default_model}"
}

mkdir -p "$OUTPUT_DIR"
log "Executing task: $TASK_ID"
run_stage 1 Research opus || die 1 "Research failed"
run_stage 2 Implement opus || die 1 "Implement failed"
if ! git diff --quiet || ! git diff --cached --quiet; then
  run_stage 3 Commit haiku || die 1 "Commit failed"
else log "No changes to commit"; fi
log "Task $TASK_ID completed"
