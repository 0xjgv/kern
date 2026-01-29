---
model: opus
---
# Stage 2: Implement

Implement the task based on research findings.

## Context

Task ID: {TASK_ID}
Hint: {HINT}

### Recent Commits

{RECENT_COMMITS}

## Instructions

1. **Get Task**: `TaskGet` with ID `{TASK_ID}` — metadata contains research findings and plan

2. **Implement**: Follow the plan from metadata, creating tasks for each step:
   - Create tasks for each step
   - Modify files in order specified by the tasks
   - Keep changes minimal and focused
   - Follow the identified pattern
   - Respect constraints

3. **Validate**: Run `make check` or appropriate validation

4. **Store Implementation Details**: `TaskUpdate` with metadata:
   - `metadata.implementation.files_changed`: Array of file paths that were changed
   - `metadata.implementation.validation`: Validation result

5. **Output**: Print `SUCCESS` or `FAILED: <reason>`
