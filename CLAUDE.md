# kern

Autonomous 7-stage development pipeline using Claude CLI for task execution with context isolation.

## Stack

- Bash, git, awk, sed
- Claude CLI

## Structure

- `kern.sh` — Pipeline orchestrator
- `install.sh` — Installation script
- `prompts/` — Stage templates (0_populate_queue → 6_review_commit)
- `agents.json` — Claude CLI agent definitions
- `SPEC.md` — Task list with checkbox state (`[ ]`, `[~]`, `[x]`)
- `.kern/` — Runtime state in current working directory (`.kern/handoff/task-<id>.md`)

## Commands

- Run: `kern` or `./kern.sh`
- Run N iterations: `kern -c N`
- Run specific task: `kern <task_id>`
- With hint: `kern --hint "guidance"`
- Verbose: `kern -v`
- Dry run: `kern -n`
- Install: `./install.sh`

## Patterns

- Tasks use markdown checkboxes: `[ ]` pending, `[~]` in-progress, `[x]` complete
- Task list ID: `kern-$PROJECT_ID-$BRANCH` (via CLAUDE_CODE_TASK_LIST_ID)
