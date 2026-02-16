---
model: opus
---
# Stage 4: Plan
Task ID: {TASK_ID}
Handoff: {HANDOFF_FILE}
1. TaskGet {TASK_ID}; Read {HANDOFF_FILE}.
2. Use codebase-analyzer to clarify any uncertain implementation details.
3. TaskUpdate metadata.plan (ordered steps) and metadata.success_criteria using: file_exists, file_contains, file_not_contains, command_succeeds, git_diff_includes.
4. Output only:
<<HANDOFF>>
## Plan
- Steps:
- Success criteria:
- Next: Implement instructions
<<END_HANDOFF>>
SUCCESS task_id=<ID>
