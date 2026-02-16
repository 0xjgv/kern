---
model: haiku
---
# Stage 0: Populate Task Queue
SPEC File: {SPEC_FILE}
1. Read `{SPEC_FILE}` and find checklist items with `[ ]` or `[~]`.
2. Run `TaskList` and index existing tasks by `metadata.spec_line`.
3. For each SPEC item missing from queue, run `TaskCreate` with:
   - `subject`: first 80 chars of task text
   - `description`: full task text
   - `metadata.spec_line`: line number
   - `metadata.spec_status`: `pending` or `in_progress`
4. Do not create duplicates when `metadata.spec_line` already exists.
5. Output only:
<<MACHINE>>
{"stage":0,"status":"success","task_id":null,"queue_empty":false,"skip":false,"summary":"queue synchronized"}
<<END_MACHINE>>
SUCCESS created=<N> existing=<M>
