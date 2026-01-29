# kern

Autonomous development pipeline — 4-stage task execution with context isolation.

## Installation

### From Source (Development)

```bash
git clone https://github.com/0xjgv/kern.git
cd kern
pip install -e .
```

### From PyPI (Coming Soon)

```bash
pip install kern
```

### Requirements

- Python >=3.13
- [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) — the AI that does the work
- [claude-agent-sdk](https://pypi.org/project/claude-agent-sdk/) — Python SDK for Claude agents
- `git` — version control

## Architecture

```m
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

```m
./
└── SPEC.md              # Task list with checkbox state ([ ], [~], [x])
```

kern is a Python package with prompts embedded in `kern.py`.

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
kern -H "focus on error handling"

# Verbose mode (shows debug info)
kern -v

# Dry run (see what would happen)
kern -n
```

### Modes

- **Iteration mode** (default): Runs Stage 0 to populate queue from SPEC.md, then iterates Stages 1-3 for each task
- **Single task mode**: `kern <task_id>` skips Stage 0 and runs Stages 1-3 for the specified task

## Features

### Project/Branch Isolation

Task list is scoped by project and branch via `CLAUDE_CODE_TASK_LIST_ID`:

```m
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

Tool restrictions are enforced programmatically via `allowed_tools` in `ClaudeAgentOptions`:

| Stage | Allowed Tools |
|-------|--------------|
| 0: Populate | Read, Glob, Grep, LS, TaskGet, TaskUpdate, TaskList, TaskCreate |
| 1: Research | Base tools + Task (agents), WebSearch, WebFetch |
| 2: Implement | Base tools + Write, Edit, Bash, Task |
| 3: Commit | Base tools + Bash (git), Edit (SPEC.md) |

Base tools: Read, Glob, Grep, LS, TaskGet, TaskUpdate, TaskList, TaskCreate

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

## Security

kern includes several security measures:

### Hint Validation

User-provided hints are validated to prevent prompt injection:

- Maximum length: 500 characters
- Blocks patterns like "ignore previous instructions", "disregard above", etc.

### Untrusted Data Wrapping

External data (hints, git diffs, commit logs) is wrapped in `<data source="...">` tags to distinguish trusted prompts from untrusted content.

### Least-Privilege Tool Access

Each stage only has access to the tools it needs (see Tool Restrictions).

## Development

```bash
# Install in development mode
pip install -e .

# Run linting
make lint

# Run tests
make test

# Run all checks
make check
```

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

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install kern
        run: pip install git+https://github.com/0xjgv/kern.git

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
- Requires `ANTHROPIC_API_KEY` secret configured in your repository
