---
model: opus
---
# Stage 5: Implement
Task ID: {TASK_ID}
Handoff: {HANDOFF_FILE}
1. TaskGet {TASK_ID}; Read {HANDOFF_FILE} and metadata.plan.
2. Implement steps, create tasks per step, keep changes minimal, follow pattern/constraints.
3. Validate with make check or appropriate command.
4. TaskUpdate metadata.implementation.files_changed and metadata.implementation.validation.
5. Output only:
<<HANDOFF>>
## Implement
- Summary:
- Files changed:
- Validation:
<<END_HANDOFF>>
SUCCESS task_id=<ID>
