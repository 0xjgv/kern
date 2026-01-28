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

{TASK}

### Previous Stage Output

{PREV_RESULT}

## Instructions

### Get Task

1. `TaskGet` → use task ID from the current task context above
2. Fallback: `TaskList` if ID missing

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
2. Mark `[x]` in SPEC.md
3. Leave uncommitted (Stage 3 commits)
4. Output: `SUCCESS`

**FAILURE:**

1. `TaskUpdate` metadata with attempt notes
2. **Tier 1** (attempts 1-2): Try different approach
3. **Tier 2** (after 3 fails): `TaskCreate` subtasks → output `DECOMPOSED`
4. **Tier 3**: `TaskUpdate` back to `pending` → output `SKIPPED`

**Rules:** Never repeat failed approaches. Read attempt metadata first.

## Output

Final line: `SUCCESS` | `DECOMPOSED` | `SKIPPED` | `FAILED`
