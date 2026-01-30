---
model: opus
---
# Stage 1: Research and Plan

Research the codebase and create an implementation plan.

## Pre-Planning Checklist

### Required (human-provided)
- [ ] Scope: What files/directories to touch?
- [ ] Excludes: What to explicitly avoid?
- [ ] Boundary: backend | frontend | fullstack
- [ ] Pattern: Existing file to follow? (path or "new")
- [ ] Done when: Success criteria?

### Failure-Derived Checks
<!-- AGENT-MANAGED: Append only, do not edit existing items -->

<!-- END AGENT-MANAGED -->

---

## Context

Task ID: {TASK_ID}
Hint: {HINT}

### Recent Commits

{RECENT_COMMITS}

## Instructions

1. **Validate Checklist**: Check for empty fields above
   - Log warnings for missing fields
   - Infer reasonable defaults, document assumptions
   - Continue unless blocked

2. **Get Task**:
   - If `{TASK_ID}` provided: `TaskGet` with ID `{TASK_ID}`
   - Otherwise: `TaskList`, select first task with status `pending` or `in_progress`
     - Mark it `in_progress` via `TaskUpdate`
     - Mark corresponding SPEC.md line `[~]` using `metadata.spec_line`

3. **Research**: Guided by checklist, use agents to explore in parallel:
   - `codebase-analyzer`: Understand current vs desired state
   - `codebase-pattern-finder`: Identify patterns (focus on Pattern reference)
   - `codebase-locator`: Find relevant files (focus on Scope, skip Excludes)
   - `web-search-researcher`: Search the web for relevant information (optional)

4. **Store Findings**: `TaskUpdate` with metadata:
   - `metadata.research.files`: Array of file paths
   - `metadata.research.pattern`: Pattern to follow
   - `metadata.research.constraints`: Array of constraints
   - `metadata.plan`: Array of implementation steps

5. **Update Checklist** (if failure detected):
   - Edit THIS file: `prompts/1_research_plan.md`
   - Append to "Failure-Derived Checks" section between markers
   - Format: `- [ ] [YYYY-MM-DD] <check> (reason: <what went wrong>)`

6. **Output**:
   - Task complete, proceed to implement: `SUCCESS task_id=<ID>`
   - Task already done (code exists, tests pass): `SUCCESS task_id=<ID> skip=true`
   - No tasks in queue: `SUCCESS task_id=none`
   - Error: `FAILED: <reason>`
