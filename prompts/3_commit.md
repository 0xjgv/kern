---
model: haiku
---
# Stage 3: Review and Commit

Review changes and commit.

## Context

### Task ID
{TASK_ID}

### Implementation Summary
Files changed: {STAGE2_FILES}
Lines: +{STAGE2_ADDED} -{STAGE2_REMOVED}
Validation: {STAGE2_VALIDATION}

### Changes
{DIFF}

### Recent Commit Style
{COMMITS}

## Instructions

### 1. Review
- `git diff` to verify changes
- Fix issues: debug prints, typos, sensitive files

### 2. Commit
```bash
git add <specific files>
git commit -m "$(cat <<'EOF'
[AUTO] Task: <task subject>

<brief description of changes>
EOF
)"
```

### 3. Sync SPEC.md
Mark completed task `[x]` in SPEC.md.

### 4. Capture Learnings
If non-obvious pattern discovered, note it.

## Output Format

On success:
```json
{
  "status": "SUCCESS",
  "task_id": "{TASK_ID}",
  "commit": "<hash>",
  "message": "<commit message>",
  "learnings": ["pattern discovered", ...]
}
```

On failure:
```json
{
  "status": "FAILED",
  "task_id": "{TASK_ID}",
  "error": "What went wrong"
}
```
