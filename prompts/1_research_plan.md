---
model: opus
---
# Stage 1: Research and Plan

Research the codebase and create an implementation plan.

## Context

Task ID: {TASK_ID}
Hint: {HINT}

### Recent Commits

{COMMITS}

### Learnings

{LEARNINGS}

## Instructions

1. **Get Task**: `TaskGet` with ID `{TASK_ID}`

2. **Research**: Use agents to explore:
   - `codebase-locator`: Find relevant files
   - `codebase-pattern-finder`: Identify patterns
   - `codebase-analyzer`: Understand current vs desired state

3. **Store Findings**: `TaskUpdate` with metadata:
   - `metadata.research.files`: Array of file paths
   - `metadata.research.pattern`: Pattern to follow
   - `metadata.research.constraints`: Array of constraints
   - `metadata.plan`: Array of implementation steps

4. **Output**: Print `SUCCESS` or `FAILED: <reason>`
