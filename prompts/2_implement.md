---
model: opus
---
# Stage 2: Implement

Implement the task based on research findings.

## Context

### Task ID
{TASK_ID}

### Hint from CC
{HINT}

### Research Summary
Files: {STAGE1_FILES}
Pattern: {STAGE1_PATTERN}
Constraints: {STAGE1_CONSTRAINTS}

### Plan
{STAGE1_PLAN}

### Recent Commits
{COMMITS}

### Learnings
{LEARNINGS}

## Instructions

### 1. Fetch Task
`TaskGet` with ID `{TASK_ID}` for full context.

### 2. Implement
Follow the plan from Stage 1:
- Modify files in order specified
- Follow the identified pattern
- Respect constraints
- Keep changes minimal and focused

### 3. Validate
Run `make check` or appropriate validation.

### 4. Update Task
On success: mark `completed`
On failure: store attempt notes in metadata

## Output Format

On success:
```json
{
  "status": "SUCCESS",
  "task_id": "{TASK_ID}",
  "files_changed": ["file1.ext", "file2.ext"],
  "lines_added": 25,
  "lines_removed": 10,
  "validation": "make check passed"
}
```

On failure:
```json
{
  "status": "FAILED",
  "task_id": "{TASK_ID}",
  "error": "What went wrong",
  "attempted": "What was tried",
  "suggestion": "What might work instead"
}
```
