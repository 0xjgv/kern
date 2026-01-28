---
model: haiku
---
# Stage 3: Review and Commit

Review changes, commit, and sync task status.

## Context

### Completed Task

{TASK}

### Changes Summary

{DIFF}

### Implementation Summary

{PREV_RESULT}

### Recent Commit Style

{COMMITS}

## Instructions

### Review

1. `git diff` and `git status`
2. Verify changes match task
3. Fix issues: debug prints, unresolved TODOs, typos, sensitive files

### Commit

```bash
git add <specific files>
git commit -m "$(cat <<'EOF'
[AUTO] Task: <description>

What changed:
- <change 1>
- <change 2>

Validation:
- make check passed
EOF
)"
```

### Sync SPEC.md

1. `TaskList` → find `completed` tasks
2. Mark matching SPEC.md lines `[x]` (use subject or `spec_ref` metadata)

### Learnings (Optional)

If non-obvious pattern or gotcha discovered, append to `LEARNINGS.md`.

## Output

Commit hash on success. Fix and retry if pre-commit fails.
