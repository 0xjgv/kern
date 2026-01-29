#!/usr/bin/env bash

# === Logging ===
debug() { ${VERBOSE:-false} && echo "[$(date '+%H:%M:%S')] [DEBUG] $1" >&2 || true; }
log() { echo "[$(date '+%H:%M:%S')] $1" >&2; }
die() { log "ERROR: $2"; exit "$1"; }

# === JSON Utilities ===
show_result() { jq -r '.result // empty' "$1"; }

# === Git Utilities ===
git_project_id() { basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; }
git_branch_safe() { local b=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown"); echo "${b//\//-}"; }

# === Claude CLI ===
alias cldd='claude --dangerously-skip-permissions'

cld() { CLAUDE_CODE_TASK_LIST_ID="$(git_project_id)-$(git_branch_safe)" cldd "$@"; }
