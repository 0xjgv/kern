---
model: opus
---
# Stage 2: Design
Task ID: {TASK_ID}
Handoff: {HANDOFF_FILE}
1. Run `TaskGet {TASK_ID}`.
2. Read `{HANDOFF_FILE}` and preserve prior stage decisions.
3. Use `codebase-pattern-finder` to identify implementation patterns and edge constraints.
4. Update `metadata.design.decisions`, `metadata.design.patterns`, `metadata.design.notes`.
5. Output only the exact contract below, no extra text:
<<MACHINE>>
{"stage":2,"status":"success","task_id":{TASK_ID},"queue_empty":false,"skip":false,"summary":"<short summary>","metadata":{"design":{"decisions":["..."],"patterns":["..."],"notes":["..."]}}}
<<END_MACHINE>>
<<HANDOFF>>
## Design
- Decisions:
- Patterns:
- Notes:
- Next: Structure instructions
<<END_HANDOFF>>
SUCCESS task_id={TASK_ID}
