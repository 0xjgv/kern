---
model: haiku
---
# Stage 3: Review and Commit

Review changes and commit.

## Context

Task ID: {TASK_ID}

### Recent Commits
{RECENT_COMMITS}

### Changes
{DIFF}

## Instructions

1. **Get Task**: `TaskGet` with ID `{TASK_ID}`
   - Extract `metadata.success_criteria` array
   - If missing, log warning and proceed with standard review

2. **Verify Success Criteria**: For each criterion:
   - `file_exists: <path>` — `ls <path>`
   - `file_contains: <path> :: <pattern>` — `grep -qE '<pattern>' <path>`
   - `file_not_contains: <path> :: <pattern>` — `! grep -qE '<pattern>' <path>`
   - `command_succeeds: <command>` — Run command, check exit 0
   - `git_diff_includes: <path>` — Check `git diff --name-only`

   **If ANY criterion fails**: Output `FAILED: Criterion not met: <criterion>` — do NOT commit

3. **Review Changes**: `git diff` to verify changes — fix debug prints, typos, sensitive files

4. **Commit** (only after verification passes):

   ```bash
   git add <specific files>
   git commit -m "$(cat <<'EOF'
   [kern] task: <subject>

   What changed:
    - <change>

   Verified:
    - <criterion>: PASS
   EOF
   )"
   ```

5. **Mark Task as Completed**: `TaskUpdate` with `status: completed`

6. **Sync SPEC.md**: Mark task `[x]` in SPEC.md

7. **Capture Learnings**: Note non-obvious patterns discovered
   - If implementation had issues that better planning would have caught:
   - Edit `prompts/1_research_plan.md`
   - Append to "Failure-Derived Checks" section between markers
   - Format: `- [ ] [YYYY-MM-DD] <check> (reason: <what went wrong>)`

8. **Output**: Print `SUCCESS` or `FAILED: <reason>`
