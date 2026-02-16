---
model: opus
---
# Stage 2: Design
Task ID: {TASK_ID}
Handoff: {HANDOFF_FILE}
1. TaskGet {TASK_ID}; Read {HANDOFF_FILE}.
2. Use codebase-pattern-finder to locate patterns and extract design decisions.
3. TaskUpdate metadata.design (decisions, patterns, risks/notes).
4. Output only:
<<HANDOFF>>
## Design
- Decisions:
- Patterns:
- Notes:
- Next: Structure instructions
<<END_HANDOFF>>
SUCCESS task_id=<ID>
