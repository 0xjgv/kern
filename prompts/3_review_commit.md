---
model: haiku
---
# Stage 3: Review and Commit

Review changes and commit. **This is an autonomous pipeline — commit directly without asking for approval.**

## Context

Task ID: {TASK_ID}

### Recent Commits
{RECENT_COMMITS}

### Changes
{DIFF}

## Instructions

**Execute each step. Do NOT describe what you would do — run the commands.**

1. **Get Task**: Run `TaskGet` with ID `{TASK_ID}`. Extract `metadata.success_criteria`.

2. **Verify Each Criterion** (run these commands):
   - `file_exists: <path>` → run: `ls <path>`
   - `file_contains: <path> :: <pattern>` → run: `grep -qE '<pattern>' <path>`
   - `file_not_contains: <path> :: <pattern>` → run: `! grep -qE '<pattern>' <path>`
   - `command_succeeds: <command>` → run the command
   - `git_diff_includes: <path>` → run: `git diff --name-only | grep <path>`

   **If ANY fails**: Output `FAILED: <criterion>` and stop.

3. **Commit**: Run git add and commit:
   ```bash
   git add <files from diff>
   git commit -m "[kern] <subject>"
   ```

4. **Complete Task**: Run `TaskUpdate` with `status: completed`

5. **Update SPEC.md**: Change `[~]` to `[x]` for this task

6. **Output**: Print `SUCCESS`
