---
model: opus
---
# Stage 1: Select and Research

Select next task from queue and research the codebase.

## Context

### Recent Commits

{COMMITS}

### Learnings

{LEARNINGS}

## Instructions

### Pre-flight

1. `git status` - warn if dirty, continue
2. `git diff HEAD~1 --stat` for context

### Select Task

1. `TaskList` to see queue
2. Find first `pending` task with empty `blockedBy`
3. `TaskGet` for full details
4. `TaskUpdate` to mark `in_progress`

If no available task: output `NO_TASK` and stop.

### Research

If task lacks research metadata, explore codebase:

- `codebase-locator`: Find relevant files (paths + lines)
- `codebase-pattern-finder`: Identify patterns to follow
- `codebase-analyzer`: Understand current vs desired state
- `web-search-researcher`: External APIs if needed

Focus on: files to modify, patterns to follow (check Learnings!), constraints/gotchas.

### Update Task

`TaskUpdate` with metadata: files, pattern, constraints, external docs.

### Sync SPEC.md

Mark task `[~]` with research notes for human visibility.

## Output

Task marked `in_progress` with research metadata. SPEC.md synced.

If no task: `NO_TASK`
