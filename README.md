# kern

Autonomous development pipeline — 4-stage task execution with context isolation.

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
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  STAGE 0         │     │  STAGE 1         │     │  STAGE 2         │     │  STAGE 3         │
│  Populate Queue  │ ──▶ │  Research & Plan │ ──▶ │  Implement       │ ──▶ │  Review & Commit │
│  (haiku)         │     │  (opus)          │     │  (opus)          │     │  (haiku)         │
│                  │     │                  │     │                  │     │                  │
│  - Parse SPEC.md │     │  - Select task   │     │  - Follow plan   │     │  - Review diff   │
│  - Create tasks  │     │  - Research code │     │  - Make changes  │     │  - Create commit │
│  - Idempotent    │     │  - Store plan    │     │  - Validate      │     │  - Mark complete │
└──────────────────┘     └──────────────────┘     └──────────────────┘     └──────────────────┘
```

## Why Stages?

1. **Context isolation**: Each stage starts fresh, avoiding 100K+ token sessions
2. **Model selection**: Cheap models (haiku) for simple work, powerful models (opus) for complex work
3. **Read-only exploration**: Stage 1 researches without modifying files
4. **Restricted commit**: Stage 3 only reviews and commits
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

## Context Injection

Each stage receives context via template placeholders:

| Context | Stage 0 | Stage 1 | Stage 2 | Stage 3 |
|---------|---------|---------|---------|---------|
| SPEC_FILE | ✓ | - | - | - |
| TASK_ID | - | ✓ | ✓ | ✓ |
| HINT | - | ✓ | ✓ | - |
| RECENT_COMMITS | - | ✓ | ✓ | ✓ |
| DIFF | - | - | - | ✓ |

Task metadata (research findings, plan) is accessed via `TaskGet`.

## Tool Restrictions

Tool restrictions are enforced via stage prompts (not script-level):

| Stage | Allowed Tools |
|-------|--------------|
| 0: Populate | TaskList, TaskCreate, Read |
| 1: Research | Read, Glob, Grep, Task, TaskGet, TaskUpdate |
| 2: Implement | All (full access) |
| 3: Commit | Read, Glob, Grep, TaskUpdate, git commands |

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
- `metadata.plan`: Implementation steps from Stage 1
- `metadata.implementation`: Changed files, validation from Stage 2

## Output Codes

Each stage outputs one of:

- `SUCCESS` — Stage completed successfully
- `FAILED: <reason>` — Stage failed with explanation

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

      - name: Install dependencies
        run: |
          sudo apt-get update && sudo apt-get install -y jq
          npm install -g @anthropic-ai/claude-code

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
