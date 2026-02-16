---
model: opus
---
# Stage 1: Research
Task ID: {TASK_ID}
Hint: {HINT}
Recent Commits:
{RECENT_COMMITS}
1. Get task: if {TASK_ID} provided -> TaskGet; else TaskList -> first pending/in_progress, TaskUpdate status=in_progress, mark SPEC line [~] using metadata.spec_line.
2. Research with agents: codebase-locator, codebase-analyzer, optional web-search-researcher.
3. TaskUpdate metadata.research.files, metadata.research.pattern, metadata.research.constraints.
4. Output only:
<<HANDOFF>>
## Research
- Summary:
- Files:
- Constraints:
- Next: Design instructions
<<END_HANDOFF>>
SUCCESS task_id=<ID> [skip=true|task_id=none]
