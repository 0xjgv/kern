---
model: opus
---
# Stage 3: Structure
Task ID: {TASK_ID}
Handoff: {HANDOFF_FILE}
1. TaskGet {TASK_ID}; Read {HANDOFF_FILE}.
2. Use codebase-locator to map files/dirs touched and existing structure.
3. TaskUpdate metadata.structure (files to touch, new files, layout notes).
4. Output only:
<<HANDOFF>>
## Structure
- Files/dirs:
- Layout notes:
- Next: Plan instructions
<<END_HANDOFF>>
SUCCESS task_id=<ID>
