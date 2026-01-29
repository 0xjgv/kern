# kern

Autonomous 3-stage development pipeline using Claude CLI for task execution with context isolation.

## Stack

- Python >=3.13, claude-agent-sdk
- Bash, git, awk

## Structure

- `kern.py` — Python pipeline module (entry: `kern`)
- `kern.sh` — Bash pipeline orchestrator
- `prompts/` — Stage templates (0_populate_queue → 3_review_commit)
- `SPEC.md` — Task list with checkbox state (`[ ]`, `[~]`, `[x]`)
- `LEARNINGS.md` — Accumulated project insights

## Commands

- Install: `make install`
- Lint: `make lint`
- Test: `make test`
- All checks: `make check`
- Run bash: `./kern.sh` or `./kern.sh N [delay]`

## Docs

- `docs/` — Incident reports and operational docs
- `thoughts/shared/` — Research and implementation plans

## Patterns

- Tasks use markdown checkboxes in SPEC.md
- Stage outputs to `/tmp/claude/kern/$PROJECT_ID/$BRANCH/`
