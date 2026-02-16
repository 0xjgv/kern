---
model: opus
---
# Stage 1: Research
Task ID: {TASK_ID}
Hint: {HINT}
Recent Commits:
{RECENT_COMMITS}
1. If Task ID is provided, run `TaskGet`.
2. If Task ID is empty, run `TaskList`, choose first pending/in_progress item, run `TaskUpdate status=in_progress`, and mark SPEC line `[~]` using `metadata.spec_line`.
3. If no pending/in_progress task exists, output queue empty contract.
4. Use `codebase-locator`, `codebase-analyzer`, and optional `web-search-researcher` to collect context.
5. Update `metadata.research.files`, `metadata.research.pattern`, `metadata.research.constraints`.
6. Output only the exact contract below, no extra text:
<<MACHINE>>
{"stage":1,"status":"success","task_id":<id|null>,"queue_empty":<true|false>,"skip":<true|false>,"summary":"<short summary>","metadata":{"research":{"files":["..."],"pattern":"...","constraints":["..."]}}}
<<END_MACHINE>>
<<HANDOFF>>
## Research
- Summary:
- Files:
- Constraints:
- Next: Design instructions
<<END_HANDOFF>>
Use exactly one final line:
- `SUCCESS task_id=none`
- `SUCCESS task_id=<ID>`
- `SUCCESS task_id=<ID> skip=true`
