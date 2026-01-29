---
model: haiku
---
# Stage 0: Populate Task Queue

Parse SPEC.md and create tasks in the queue idempotently.

## Context

SPEC File: {SPEC_FILE}

## Instructions

1. **Read SPEC.md**: Get all items with `[ ]` (pending) or `[~]` (in-progress)

2. **Check Existing Tasks**: `TaskList` to see current queue

3. **Create Missing Tasks**: For each SPEC item not in queue:
   - `TaskCreate` with:
     - subject: First 80 chars of task description
     - description: Full task text
     - metadata.spec_line: Line number in SPEC.md
     - metadata.spec_status: `pending` or `in_progress`
   - Skip if task with same `spec_line` already exists

4. **Output**: Print `SUCCESS created=N existing=M` where N=new tasks, M=already existed
