---
model: haiku
---
# Stage 6: Review and Commit
Task ID: {TASK_ID}
Recent Commits:
{RECENT_COMMITS}
Changes:
{DIFF}
1. TaskGet {TASK_ID}; read metadata.success_criteria.
2. Verify criteria with commands: file_exists->ls, file_contains->grep -qE, file_not_contains->! grep -qE, command_succeeds->run, git_diff_includes->git diff --name-only | grep.
3. If any fail: output FAILED: <criterion> and stop.
4. Commit: git add <files from diff>; git commit -m "[kern] <subject>".
5. TaskUpdate status=completed; update SPEC.md [~]->[x].
6. Output only:
<<HANDOFF>>
## Review & Commit
- Verified:
- Commit:
<<END_HANDOFF>>
SUCCESS
