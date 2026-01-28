---
model: haiku
---
# Stage 0: Generate Task Queue

Populate Claude Code's task system from SPEC.md.

## Context

### Learnings

{LEARNINGS}

## Instructions

1. Run `TaskList` to see existing tasks
2. Read `SPEC.md` and find `- [ ]` pending tasks not yet in queue
3. For each new task, use `TaskCreate`:
   - `subject`: Task title (imperative form)
   - `description`: Context from SPEC.md including any notes
   - `activeForm`: Present continuous (e.g., "Adding retry logic")
   - `metadata.spec_ref`: Original SPEC.md line for sync
4. Set `addBlockedBy` via `TaskUpdate` for dependencies (indented tasks depend on parent)
5. Skip tasks that already exist in queue (match by subject)

**Complex tasks**: Decompose "Add X and update Y" into separate tasks with blocking relationships.

## Output

Summary: tasks created, skipped, dependencies set.

If no pending tasks in SPEC.md: `NO_TASKS`
