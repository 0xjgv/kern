---
model: opus
---
# Stage 2: Implement

Implement the task based on research findings in collaboration with 3 agent teammates.

## Context

Task ID: {TASK_ID}
Hint: {HINT}

### Recent Commits

{RECENT_COMMITS}

## Rules

- **DO NOT run `git commit`, `git add`, or any git write commands.** Stage 3 handles commits.
- **DO NOT modify pipeline files** (`kern.sh`, `prompts/`, `install.sh`, `scripts/`, `.github/`). These are infrastructure, not task scope.
- Only change files specified in the task plan. If the plan is unclear, change less, not more.

## Instructions

1. **Get Task**: `TaskGet` with ID `{TASK_ID}` — metadata contains research findings and plan

2. **Implement**: Follow the plan from metadata:
   - Modify files in order specified by the plan
   - Keep changes minimal and focused
   - Follow the identified pattern
   - Respect constraints

3. **Validate**: Run validation commands from `metadata.success_criteria` if available

4. **Store Implementation Details**: `TaskUpdate` with metadata:
   - `metadata.implementation.files_changed`: Array of file paths that were changed
   - `metadata.implementation.validation`: Validation result

5. **Output**: Print `SUCCESS` or `FAILED: <reason>`
