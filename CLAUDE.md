# kern

Autonomous 4-stage development pipeline using Claude CLI for task execution with context isolation.

## Stack

- Bash, jq, git, awk
- Claude CLI

## Structure

- `kern.sh` — Pipeline orchestrator
- `install.sh` — Installation script
- `prompts/` — Stage templates (0_populate_queue → 3_review_commit)
- `agents.json` — Claude CLI agent definitions
- `SPEC.md` — Task list with checkbox state (`[ ]`, `[~]`, `[x]`)
- `LEARNINGS.md` — Accumulated project insights

## Commands

- Run: `./kern.sh`
- Run N iterations: `./kern.sh N [delay]`
- Verbose: `./kern.sh -v`
- Dry run: `./kern.sh -n`
- Install: `./install.sh`

## Patterns

- Tasks use markdown checkboxes: `[ ]` pending, `[~]` in-progress, `[x]` complete
- Stage outputs to `/tmp/claude/kern/$PROJECT_ID/$BRANCH/`
