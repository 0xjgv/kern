---
model: opus
---
# Stage 4: Plan
Task ID: {TASK_ID}
Handoff: {HANDOFF_FILE}
1. Run `TaskGet {TASK_ID}` and read `{HANDOFF_FILE}`.
2. Use `codebase-analyzer` for unresolved implementation details.
3. Build ordered implementation steps.
4. Build normalized success criteria using only:
   `file_exists`, `file_contains`, `file_not_contains`, `command_succeeds`, `git_diff_includes`.
5. Update `metadata.plan` and `metadata.success_criteria`.
6. Output only the exact contract below, no extra text:
<<MACHINE>>
{"stage":4,"status":"success","task_id":{TASK_ID},"queue_empty":false,"skip":false,"summary":"<short summary>","criteria":[{"kind":"file_exists","value":"README.md"},{"kind":"file_contains","value":"README.md::Validation"}],"metadata":{"plan":{"steps":["..."]}}}
<<END_MACHINE>>
<<HANDOFF>>
## Plan
- Steps:
- Success criteria:
- Next: Implement instructions
<<END_HANDOFF>>
SUCCESS task_id={TASK_ID}
