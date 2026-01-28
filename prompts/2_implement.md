---
model: opus
---
# Stage 2: Plan and Implement

Implement the current task based on research findings.

## Context

### Recent Commits

{COMMITS}

### Learnings

{LEARNINGS}

### Current Task

ID: {TASK_ID}

{TASK}

### Previous Stage Output

{PREV_RESULT}

## Instructions

### Get Task

`TaskGet` with ID `{TASK_ID}` for full details including metadata.

### Plan

1. List changes needed (files, functions, lines)
2. Order logically (dependencies first)
3. If 6+ files: decompose with `TaskCreate` subtasks

### Implement

- Follow patterns from research metadata
- Keep changes minimal and focused
- Avoid over-engineering

### Validate

Run `make check` or task-specific validation.

### Handle Results

**SUCCESS:**

1. `TaskUpdate` → mark `completed`
2. Leave uncommitted (Stage 3 commits)

**FAILURE:**

1. `TaskUpdate` metadata with attempt notes
2. **Tier 1** (attempts 1-2): Try different approach
3. **Tier 2** (after 3 fails): `TaskCreate` subtasks, keep task `in_progress`
4. **Tier 3**: `TaskUpdate` back to `pending` (skip this iteration)

**Rules:** Never repeat failed approaches. Read attempt metadata first.

## Output

Summary of actions taken and final task state.
