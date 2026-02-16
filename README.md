# kern

Autonomous development pipeline — 7-stage task execution with context isolation.

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/0xjgv/kern/main/install.sh | sh
```

### Requirements

- [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) — the AI that does the work
- `git` — version control

### Update

```bash
kern --update
```

## Architecture

```
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  STAGE 0         │ │  STAGE 1         │ │  STAGE 2         │ │  STAGE 3         │ │  STAGE 4         │ │  STAGE 5         │ │  STAGE 6         │
│  Populate Queue  │ │  Research        │ │  Design          │ │  Structure       │ │  Plan            │ │  Implement       │ │  Review & Commit │
│  (haiku)         │ │  (opus)          │ │  (opus)          │ │  (opus)          │ │  (opus)          │ │  (opus)          │ │  (haiku)         │
│                  │ │                  │ │                  │ │                  │ │                  │ │                  │ │                  │
│  - Parse SPEC.md │ │  - Select task   │ │  - Design choices│ │  - File layout   │ │  - Steps + crit  │ │  - Make changes  │ │  - Review diff   │
│  - Create tasks  │ │  - Research code │ │  - Patterns      │ │  - Touch list    │ │  - Store plan    │ │  - Validate      │ │  - Create commit │
│  - Idempotent    │ │  - Store findings│ │  - Store design  │ │  - Store structure│ │                  │ │                  │ │  - Mark complete │
└──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Why Stages?

1. **Context isolation**: Each stage starts fresh, avoiding 100K+ token sessions
2. **Model selection**: Cheap models (haiku) for simple work, powerful models (opus) for complex work
3. **Read-only exploration**: Stages 1-4 research/design/structure/plan without modifying files
4. **Restricted commit**: Stage 6 only reviews and commits
5. **Task queue**: Stage 0 syncs SPEC.md → TaskList for structured tracking

## Project Setup

In your project, create:

```
./
└── SPEC.md              # Task list with checkbox state ([ ], [~], [x])
```

kern installs to `~/.local/share/kern/` with its prompts bundled.

## Usage

```bash
# Show help
kern --help

# Run up to 5 tasks (default)
kern

# Run up to 10 tasks
kern -c 10

# Run specific task by ID
kern 7

# Run with hint for guidance
kern --hint "focus on error handling"

# Verbose mode (shows debug info)
kern -v

# Dry run (see what would happen)
kern -n
```

## Features

### Project/Branch Isolation

Task list is scoped by project and branch via `CLAUDE_CODE_TASK_LIST_ID`:

```
kern-$PROJECT_ID-$BRANCH
```

Prevents collisions between repos and git worktrees.

### Runtime State

All generated runtime state is written inside the current working directory:
`.kern/`

Handoff files are append-only per task:
`.kern/handoff/task-<id>.md`

## Context Injection

Each stage receives context via template placeholders:

| Context | Stage 0 | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Stage 5 | Stage 6 |
|---------|---------|---------|---------|---------|---------|---------|---------|
| SPEC_FILE | ✓ | - | - | - | - | - | - |
| TASK_ID | - | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| HINT | - | ✓ | - | - | - | - | - |
| RECENT_COMMITS | - | ✓ | - | - | - | - | ✓ |
| DIFF | - | - | - | - | - | - | ✓ |
| HANDOFF_FILE | - | - | ✓ | ✓ | ✓ | ✓ | ✓ |

Task metadata (research/design/structure/plan) is accessed via `TaskGet`.

## Tool Restrictions

Tool restrictions are enforced via `--allowedTools` flag in kern.sh:

| Stage | Mode | Allowed Tools |
|-------|------|--------------|
| 0: Populate | Read-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskCreate, TaskUpdate |
| 1: Research | Read-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskUpdate, Task |
| 2: Design | Read-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskUpdate, Task |
| 3: Structure | Read-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskUpdate, Task |
| 4: Plan | Read-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskUpdate, Task |
| 5: Implement | Full access | All tools (--dangerously-skip-permissions) |
| 6: Commit | Commit-only | Read, Glob, Grep, LS, TaskGet, TaskList, TaskUpdate, Bash |

**Note**: Stages 0, 1-4, 6 use `cld_s0()`, `cld_s1()`, `cld_s3()` respectively, pre-approving tools via CLI flag.
Stage 5 uses `cld_rw()` with full permissions for file edits and bash commands.

## Task State

Tasks are tracked in two places:

**SPEC.md** — Human-readable task list with checkbox state:
```markdown
- [ ] Pending task
- [~] In-progress task
- [x] Completed task
```

**TaskList** — Claude's task queue with metadata:
- `metadata.spec_line`: Line number in SPEC.md
- `metadata.research`: Files, patterns, constraints from Stage 1
- `metadata.design`: Design decisions from Stage 2
- `metadata.structure`: File layout decisions from Stage 3
- `metadata.plan`: Implementation steps from Stage 4
- `metadata.success_criteria`: Verification criteria from Stage 4
- `metadata.implementation`: Changed files, validation from Stage 5

## Output Codes

Each stage outputs one of:

- `SUCCESS` — Stage completed successfully (may include metadata like `task_id=N`, `skip=true`)
- `FAILED: <reason>` — Stage failed with explanation

Stage 0 outputs `SUCCESS created=N existing=M` showing queue population stats.

## Debugging

Check SPEC.md for task state:

```bash
grep '\[\(~\| \|x\)\]' SPEC.md
```

Task metadata is stored in Claude's TaskList (view via `TaskList` tool in a Claude session).

## Releasing

To cut a new release:

```bash
./scripts/release.sh 0.1.5
```

Or manually: **Actions → Release → Run workflow** → enter version

The workflow:

1. Validates version format and checks tag doesn't exist
2. Injects version into `kern.sh`
3. Creates tarball with `kern.sh`, `prompts/`, `README.md`
4. Creates git tag and GitHub Release with auto-generated notes

No local tags needed — the workflow handles everything.

## CI/CD

Example GitHub Actions workflow to run kern on your repo:

```yaml
name: kern

on:
  workflow_dispatch:
    inputs:
      iterations:
        description: 'Number of iterations'
        default: '5'

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Claude CLI
        run: npm install -g @anthropic-ai/claude-code

      - name: Install kern
        run: curl -fsSL https://raw.githubusercontent.com/0xjgv/kern/main/install.sh | sh

      - name: Run kern
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: kern -c ${{ inputs.iterations }}

      - name: Push changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git push
```

**Notes:**

- Uses `workflow_dispatch` for manual triggers — adjust trigger as needed
- Requires Claude Code CLI
