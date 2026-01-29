#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# === Logging ===
debug() { ${VERBOSE:-false} && echo "[$(date '+%H:%M:%S')] [DEBUG] $1" >&2 || true; }
log() { echo "[$(date '+%H:%M:%S')] $1" >&2; }
die() { log "ERROR: $2"; exit "$1"; }

# === Git Utilities ===
git_project_id() { basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; }
git_branch_safe() { local b=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown"); echo "${b//\//-}"; }

# === Claude CLI ===
cldd() { claude --dangerously-skip-permissions "$@"; }
cld() { CLAUDE_CODE_TASK_LIST_ID="$(git_project_id)-$(git_branch_safe)" CLAUDE_CODE_ENABLE_TASKS=true cldd "$@"; }

PROJECT_ID=$(git_project_id) BRANCH=$(git_branch_safe)
export CLAUDE_CODE_TASK_LIST_ID="kern-$PROJECT_ID-$BRANCH"
VERBOSE=false DRY_RUN=false HINT=""
PROMPTS="$SCRIPT_DIR/prompts"

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

build_prompt() {
  local tpl="$1"
  # Strip YAML frontmatter, inject only TASK_ID, HINT, and DIFF
  # Stage gets everything else via TaskGet
  TASK_ID="$TASK_ID" HINT="$HINT" DIFF="$(git diff --stat 2>/dev/null | head -30)" \
  awk '/^---$/ { if (++fm == 2) next } fm < 2 && fm > 0 { next }
       { gsub(/\{TASK_ID\}/, ENVIRON["TASK_ID"])
         gsub(/\{HINT\}/, ENVIRON["HINT"])
         gsub(/\{DIFF\}/, ENVIRON["DIFF"]); print }' "$tpl"
}

run_stage() {
  local num="$1" name="$2" default_model="${3:-opus}"
  local tpl=$(echo "$PROMPTS"/${num}_*.md)
  local model=$(awk '/^---$/{if(++c==2)exit} c==1&&/^model:/{print $NF}' "$tpl")

  log "Stage $num: $name"

  if $DRY_RUN; then
    log "[DRY-RUN] Would run: cld --model ${model:-$default_model}"
    return 0
  fi

  # Trust Claude exit code; check Task metadata for visibility
  build_prompt "$tpl" | cld --model "${model:-$default_model}" \
    $($VERBOSE && echo "--verbose") -p "$(cat -)"
}

log "Executing task: $TASK_ID"
run_stage 1 "Research & Planning" opus || die 1 "Research failed"
run_stage 2 "Implement" opus || die 1 "Implement failed"
if ! git diff --quiet || ! git diff --cached --quiet; then
  run_stage 3 "Commit & Review" haiku || die 1 "Commit failed"
else log "No changes to commit"; fi
log "Task $TASK_ID completed"
