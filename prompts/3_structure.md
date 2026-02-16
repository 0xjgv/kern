---
model: opus
---
# Stage 3: Structure
Task ID: {TASK_ID}
Handoff: {HANDOFF_FILE}
1. Run `TaskGet {TASK_ID}`.
2. Read `{HANDOFF_FILE}` for Research and Design constraints.
3. Use `codebase-locator` to map files/directories that must change.
4. Update `metadata.structure.files`, `metadata.structure.new_files`, `metadata.structure.layout_notes`.
5. Put normalized planned files in `planned_files` as repo-relative paths.
6. Output only the exact contract below, no extra text:
<<MACHINE>>
{"stage":3,"status":"success","task_id":{TASK_ID},"queue_empty":false,"skip":false,"summary":"<short summary>","planned_files":["path/a","path/b"],"metadata":{"structure":{"files":["..."],"new_files":["..."],"layout_notes":["..."]}}}
<<END_MACHINE>>
<<HANDOFF>>
## Structure
- Files/dirs:
- Layout notes:
- Next: Plan instructions
<<END_HANDOFF>>
SUCCESS task_id={TASK_ID}
