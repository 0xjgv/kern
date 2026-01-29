---
model: opus
---
# Stage 1: Research and Plan

Research the codebase for the given task and create an implementation plan.

## Context

### Task ID
{TASK_ID}

### Hint from CC
{HINT}

### Recent Commits
{COMMITS}

### Learnings
{LEARNINGS}

## Instructions

### 1. Fetch Task
`TaskGet` with ID `{TASK_ID}` for full details.

### 2. Research
Use agents to explore the codebase:
- `codebase-locator`: Find relevant files
- `codebase-pattern-finder`: Identify patterns to follow
- `codebase-analyzer`: Understand current vs desired state

Focus on: files to modify, patterns to follow, constraints.

### 3. Create Plan
List concrete changes needed:
1. Which files to modify
2. What changes in each file
3. Order of operations

### 4. Update Task
Store research findings in task metadata.

## Output Format

You MUST output valid JSON in this exact structure:

```json
{
  "status": "SUCCESS",
  "task_id": "{TASK_ID}",
  "research": {
    "files": ["path/to/file:lines", ...],
    "pattern": "Description of pattern to follow",
    "constraints": ["constraint 1", "constraint 2"]
  },
  "plan": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ]
}
```

If research fails, output:
```json
{
  "status": "FAILED",
  "task_id": "{TASK_ID}",
  "error": "Description of what went wrong"
}
```
