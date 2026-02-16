---
model: opus
---
# Stage 5: Implement
Task ID: {TASK_ID}
Handoff: {HANDOFF_FILE}
Hint: {HINT}
1. Run `TaskGet {TASK_ID}`.
2. Read `{HANDOFF_FILE}`, `metadata.plan`, and `metadata.success_criteria`.
3. Implement minimally according to plan and existing patterns.
4. Run validation commands from plan (or closest project equivalent).
5. Update `metadata.implementation.files_changed` and `metadata.implementation.validation`.
6. Output only the exact contract below, no extra text:
<<MACHINE>>
{"stage":5,"status":"success","task_id":{TASK_ID},"queue_empty":false,"skip":false,"summary":"<short summary>","metadata":{"implementation":{"files_changed":["..."],"validation":["..."]}}}
<<END_MACHINE>>
<<HANDOFF>>
## Implement
- Summary:
- Files changed:
- Validation:
<<END_HANDOFF>>
SUCCESS task_id={TASK_ID}
