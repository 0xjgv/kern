---
model: haiku
---
# Stage 3: Review and Commit

Review changes and commit.

## Context

Task ID: {TASK_ID}

### Changes

{DIFF}

### Recent Commit Style

{COMMITS}

## Instructions

1. **Get Task**: `TaskGet` with ID `{TASK_ID}` for context

2. **Review Changes**: `git diff` to verify changes — fix debug prints, typos, sensitive files

3. **Commit**:

   ```bash
   git add <specific files>
   git commit -m "$(cat <<'EOF'
   [kern] task: <subject line>
   <description>

   What changed:
    - <what was done>
    - <what was done>

   Validation:
    - <validation result>
    - <make check passed>
   EOF
   )"
   ```

4. **Mark Task as Completed**: `TaskUpdate` with `status: completed`

5. **Sync SPEC.md**: Mark task `[x]` in SPEC.md

6. **Capture Learnings**: Note non-obvious patterns discovered

7. **Output**: Print `SUCCESS` or `FAILED: <reason>`
