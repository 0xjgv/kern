#!/usr/bin/env

function gitsearch {
  search=$1
  if [ $search ]; then
    git rev-list --all | xargs git grep $search
  else
    echo "Missing search value"
  fi
}

alias cldd='claude --dangerously-skip-permissions'

# Claude CLI wrapper with auto-scoped task list
function cld() {
  local repo=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
  local branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
  CLAUDE_CODE_TASK_LIST_ID="${repo}-${branch//\//-}" cldd "$@"
}
