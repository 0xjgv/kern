# kern

Autonomous 3-stage development pipeline using Claude CLI for task execution with context isolation.

## Stack

- jq, git, awk
- Claude CLI
- Bash

## Structure

- `kern.sh` — Pipeline orchestrator
- `prompts/` — Stage templates (1_research, 2_implement, 3_commit)
- `SPEC.md` — Task list with checkbox state (`[ ]`, `[~]`, `[x]`)
- `LEARNINGS.md` — Accumulated project insights

## Commands

- Run: `./kern.sh`
- Run N iterations: `./kern.sh N [delay]`
- Verbose: `./kern.sh -v`
- Dry run: `./kern.sh -n`
- Debug: `jq '.result' /tmp/claude/kern/$PROJECT/$BRANCH/stage*.json`

## Patterns

- Tasks use markdown checkboxes: `[ ]` pending, `[~]` in-progress, `[x]` complete
- Stage outputs to `/tmp/claude/kern/$PROJECT_ID/$BRANCH/`
- Retry with exponential backoff on transient failures
