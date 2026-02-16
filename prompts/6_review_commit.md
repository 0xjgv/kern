---
model: haiku
---
# Stage 6: Review and Commit
Task ID: {TASK_ID}
Recent Commits:
{RECENT_COMMITS}
Changes:
{DIFF}
1. Run `TaskGet {TASK_ID}`.
2. Do final review of changed files for obvious regressions only.
3. Commit only current task changes: `git add <files from diff>` then `git commit -m "[kern] <subject>"`.
4. Run `TaskUpdate status=completed`.
5. Mark corresponding SPEC line `[x]` using `metadata.spec_line`.
6. Output only the exact contract below, no extra text:
<<MACHINE>>
{"stage":6,"status":"success","task_id":{TASK_ID},"queue_empty":false,"skip":false,"summary":"<short summary>"}
<<END_MACHINE>>
<<HANDOFF>>
## Review & Commit
- Reviewed:
- Commit:
<<END_HANDOFF>>
SUCCESS
