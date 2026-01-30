---
model: opus
---
# Stage 1: Research and Plan

Research the codebase and create an implementation plan.

## Context

Task ID: {TASK_ID}
Hint: {HINT}

### Recent Commits

{RECENT_COMMITS}

## Instructions

1. **Get Task**:
   - If `{TASK_ID}` provided: `TaskGet` with ID `{TASK_ID}`
   - Otherwise: `TaskList`, select first task with status `pending` or `in_progress`
     - Mark it `in_progress` via `TaskUpdate`
     - Mark corresponding SPEC.md line `[~]` using `metadata.spec_line`

2. **Research**: Use agents to explore the codebase in parallel:
   - `codebase-analyzer`: Understand current vs desired state
   - `codebase-pattern-finder`: Identify patterns
   - `codebase-locator`: Find relevant files
   - `web-search-researcher`: Search the web for relevant information (optional)

3. **Store Findings**: `TaskUpdate` with metadata:
   - `metadata.research.files`: Array of file paths
   - `metadata.research.pattern`: Pattern to follow
   - `metadata.research.constraints`: Array of constraints
   - `metadata.plan`: Array of implementation steps

4. **Output**:
   - Task complete, proceed to implement: `SUCCESS task_id=<ID>`
   - Task already done (code exists, tests pass): `SUCCESS task_id=<ID> skip=true`
   - No tasks in queue: `SUCCESS task_id=none`
   - Error: `FAILED: <reason>`
