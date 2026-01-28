# kern

Autonomous development pipeline — 3-stage task execution with context isolation and debuggability.

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/0xjgv/kern/main/install.sh | sh
```

### Requirements

- [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) — the AI that does the work
- `jq` — JSON processing
- `git` — version control

### Update

```bash
kern --update
```

## Architecture

```
┌─────────────────────────────────┐     ┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│  STAGE 1: Research              │     │  STAGE 2: Implement             │     │  STAGE 3: Commit                │
│  (read-only)                    │ ──▶ │  (full access)                  │ ──▶ │  (git-only)                     │
│                                 │     │                                 │     │                                 │
│  - Select task from SPEC.md    │     │  - Create plan from research    │     │  - Review changes               │
│  - Research codebase            │     │  - Implement changes            │     │  - Check for issues             │
│  - Document findings            │     │  - Run validation               │     │  - Create commit                │
│  - Output: task + research      │     │  - Handle failures              │     │  - Update learnings             │
└─────────────────────────────────┘     └─────────────────────────────────┘     └─────────────────────────────────┘
        │                                       │                                       │
        ▼                                       ▼                                       ▼
   stage1.json                             stage2.json                             stage3.json
```

## Why 3 Stages?

1. **Context isolation**: Each stage starts fresh, avoiding 100K+ token sessions
2. **Debuggability**: Stage outputs in `/tmp/claude/kern/...` are inspectable
3. **Read-only exploration**: Stage 1 can't accidentally break things
4. **Restricted commit**: Stage 3 can only run git commands
5. **Natural coupling**: Research+Plan and Implement+Validate are tightly coupled

## Project Setup

In your project, create:

```
./
├── SPEC.md              # Task list + research notes + attempt history
└── LEARNINGS.md         # Accumulated insights (grows over time)
```

kern installs to `~/.local/share/kern/` with its prompts bundled.

## Usage

```bash
# Show help
kern --help

# Run 5 iterations (default)
kern

# Run 10 iterations with 30s delay
kern 10 30

# Verbose mode (shows debug info)
kern -v 5

# Dry run (see what would happen without executing)
kern -n

# Check stage outputs (project/branch scoped)
jq '.result' /tmp/claude/kern/$PROJECT/$BRANCH/stage*.json
```

## Features

### Retry Logic
Transient failures (API errors, network issues) retry up to 3 times with exponential backoff.

### Stale Lock Detection
If a previous run was killed, the lock file is automatically cleaned up based on PID.

### SPEC.md Validation
After each stage, SPEC.md is validated for:
- Malformed task markers
- Multiple in-progress tasks (should only be one)

### Resume Logic
Pipeline state is inferred from SPEC.md + stage files (no state file needed):
- If an in-progress task exists (`[~]`) and stage files are present, resumes from the appropriate stage
- Stage files are cleaned up after each successful iteration

### Project/Branch Isolation
Output directory is scoped by project and branch: `/tmp/claude/kern/$PROJECT_ID/$BRANCH`
- Prevents collisions between repos and git worktrees
- Lock files are also scoped: `/tmp/claude/kern/$PROJECT_ID-$BRANCH.lock.d`

## Context Injection

Each stage receives pre-built context (no tool calls needed to find it):

| Context | Stage 1 | Stage 2 | Stage 3 |
|---------|---------|---------|---------|
| LEARNINGS.md | ✓ | ✓ | - |
| Recent commits | ✓ | ✓ | ✓ (for style) |
| Current task + research | - | ✓ | ✓ (task only) |
| Git diff | - | - | ✓ |

## Tool Restrictions

Tool restrictions are enforced via stage prompts (not script-level enforcement):

| Stage | Allowed Tools |
|-------|--------------|
| Research | Read, Glob, Grep, Task, WebSearch, WebFetch |
| Implement | All (full access) |
| Commit | Read, Glob, Grep, git add, git commit, git status, git diff |

## Task State in SPEC.md

```markdown
- [ ] Pending task
- [~] In-progress task
  > **Research:**
  >   - Files: path:lines
  >   - Pattern: what to follow
  >   - Constraint: blockers
  > **Attempt 1:** what failed
  > **Attempt 2:** different approach that also failed
- [x] Completed task
  > **Research:** (preserved for reference)
```

## Failure Handling

**Tier 1 - Different approach** (attempts 1-2):
- Stage 2 reads attempt notes and tries alternative

**Tier 2 - Decompose** (after 3 attempts):
- Stage 2 breaks task into subtasks
- Next iteration works on subtasks individually

**Tier 3 - Skip** (if subtasks fail):
- Task reverts to `[ ]` with notes preserved
- Pipeline moves to next task
- Will return to skipped task in future iteration

## Output Codes

Stage 2 outputs one of:
- `SUCCESS` - Task completed, ready for Stage 3
- `DECOMPOSED` - Task broken into subtasks, skip to next iteration
- `SKIPPED` - Task blocked, moved to next task
- `FAILED` - Exhausted approaches, needs manual help

## Debugging

1. Check stage outputs:
   ```bash
   jq '.result' /tmp/claude/kern/$PROJECT/$BRANCH/stage*.json
   ```

2. View full transcript:
   ```bash
   jq '.' /tmp/claude/kern/$PROJECT/$BRANCH/stage2.json | less
   ```

3. Check SPEC.md for attempt notes:
   ```bash
   grep -A 10 '\[~\]' SPEC.md
   ```

## Context Budget

| Stage | Injected | Typical Total | Notes |
|-------|----------|---------------|-------|
| Research | ~2K | 30-50K | Explores broadly, outputs compressed |
| Implement | ~3K | 50-100K | Bulk of work, focused by task |
| Commit | ~1K | 10-20K | Minimal, just review and commit |
