# kern

Autonomous development pipeline using a Python CLI and `claude_code_sdk` with strict stage contracts.

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/0xjgv/kern/main/install.sh | sh
```

### Requirements

- [Claude CLI](https://docs.anthropic.com/en/docs/claude-code)
- `python3`
- `git`

Installer behavior:
- Creates managed virtualenv at `~/.local/share/kern/.venv`
- Symlinks `kern` to `~/.local/bin/kern`

### Update

```bash
kern --update
```

## Architecture

```
Stage 0 Populate Queue
  -> Stage 1 Research
  -> Stage 2 Design
  -> Stage 3 Structure
  -> Stage 4 Plan
  -> Stage 5 Implement
  -> Runtime Validation + Evaluation (soft gate)
       - fail critical checks -> one fix retry (Stage 5) -> re-validate/re-score
  -> Stage 6 Review & Commit
```

## Usage

```bash
kern --help
kern
kern -c 10
kern 7
kern --hint "focus on validation edge cases"
kern -v
kern -n
```

## Runtime State

All runtime state is written under the current working directory `.kern/`:

- `.kern/handoff/task-<id>.md` append-only stage handoff + validation/evaluation notes
- `.kern/state/task-<id>.json` normalized task state (planned files, success criteria)
- `.kern/reports/task-<id>.jsonl` per-attempt evaluation reports
- `.kern/runs/<run_id>/events.jsonl` per-stage execution events (duration, usage, cost, status)

## Stage Output Contract

Stages `1..6` must emit machine-parseable output:

1. `<<MACHINE>>` block containing one JSON object
2. `<<HANDOFF>>` block for stages `1..5` (stage 6 optional)
3. Exact final success line:
   - Stage 1: `SUCCESS task_id=<ID>` or `SUCCESS task_id=none` and optional `skip=true`
   - Stages 2-5: `SUCCESS task_id=<ID>`
   - Stage 6: `SUCCESS`

Malformed stage output fails fast.

## Validation and Soft Gate

After Stage 5, runtime validates success criteria using:

- `file_exists`
- `file_contains`
- `file_not_contains`
- `command_succeeds`
- `git_diff_includes`

Criteria are read from normalized Stage 4 machine output stored in `.kern/state/task-<id>.json`.  
Handoff parsing is retained as compatibility fallback.

Soft gate policy:

- Critical failures (`file_exists`, `file_contains`, `file_not_contains`, `command_succeeds`) trigger one automatic fix retry.
- If critical failures remain after retry, task fails and Stage 6 is skipped.
- Advisory failures (scope drift, `git_diff_includes`, score regression) are recorded but do not block commit.

## Stage Policy

Policy is enforced through SDK options (`allowed_tools`, `permission_mode`, `model`):

| Stage | Mode | Tool Policy |
|-------|------|-------------|
| 0: Populate | Read-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskCreate, TaskUpdate |
| 1: Research | Read-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskUpdate, Task |
| 2: Design | Read-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskUpdate, Task |
| 3: Structure | Read-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskUpdate, Task |
| 4: Plan | Read-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskUpdate, Task |
| 5: Implement | Full access | `permission_mode=bypassPermissions` |
| 6: Commit | Commit-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskUpdate, Bash |

## Context Injection

Each prompt receives placeholders rendered by runtime:

| Context | Stage 0 | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Stage 5 | Stage 6 |
|---------|---------|---------|---------|---------|---------|---------|---------|
| SPEC_FILE | ✓ | - | - | - | - | - | - |
| TASK_ID | - | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| HINT | - | ✓ | - | - | - | ✓ | - |
| RECENT_COMMITS | - | ✓ | - | - | - | - | ✓ |
| DIFF | - | - | - | - | - | - | ✓ |
| HANDOFF_FILE | - | - | ✓ | ✓ | ✓ | ✓ | ✓ |

## Authentication

`kern` supports either:

- Logged-in Claude CLI session (`claude auth`), or
- `ANTHROPIC_API_KEY` environment variable

`ANTHROPIC_API_KEY` is not required if a valid CLI login session exists.

## Python API

```python
from kern.runtime import run

exit_code = run(
    task_id=None,
    max_tasks=5,
    hint="",
    dry_run=False,
    verbose=False,
)
```

## Releasing

```bash
./scripts/release.sh 0.1.5
```

Release workflow:

1. Validates version and tag.
2. Injects version into `src/kern/version.py` and `pyproject.toml`.
3. Packages Python source + prompts + install assets.
4. Publishes `kern.tar.gz` with checksum.
