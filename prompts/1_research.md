---
model: opus
---
# Stage 1: Select and Research

You are an autonomous senior software engineer agent. Your task is to select the next task and research the codebase to prepare for implementation.

## Context

### Recent Commits

{COMMITS}

### Learnings

{LEARNINGS}

## Instructions

### Step 1: Pre-flight

1. Run `git status` - if dirty tree, warn and continue (don't stash/commit)
2. Run `git diff HEAD~1 --stat` for recent context

### Step 2: Select Task

Read `SPEC.md` and find:

1. `- [~]` in-progress task → Continue that task
2. Else first `- [ ]` unchecked task → Mark as `- [~]`

If no suitable task exists (all complete or blocked), output "NO_TASK" and stop.

### Step 3: Research

If the task has no research notes (no `> **Research:**` block), explore the codebase:

1. Use `codebase-locator` to find relevant files (paths + line numbers)
2. Use `codebase-pattern-finder` to identify patterns to follow
3. Use `codebase-analyzer` to understand current vs desired state
4. Use `web-search-researcher` for external APIs if needed

Focus on:

- Which files need modification
- Existing patterns to follow (check Learnings above first!)
- Constraints and gotchas that could affect implementation
- External documentation if needed

### Step 4: Update SPEC.md

Add research notes under the task:

```markdown
- [~] Task description
  > **Research:**
  >   - Files: <path:lines>, <path:lines>
  >   - Pattern: <what pattern to follow, reference file>
  >   - Constraint: <blockers or warnings>
  >   - External: <API docs URL if needed>
```

Keep notes concise but complete enough for a fresh context to implement.

## Output

On completion, the task in `SPEC.md` should be marked `[~]` with research notes.

If no task available, output exactly: `NO_TASK`
