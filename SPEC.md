# Tasks

- [x] Update README.md to reflect current state: review accuracy of documentation, update any outdated sections, ensure examples match current behavior, and improve clarity where needed

## Python Port (claude-agent-sdk)

### Phase 1: Foundation

- [x] Create Python package structure: `kern.py` as main module with `pyproject.toml` package configuration (requires-python >=3.13, claude-agent-sdk dependency)
- [x] Implement git utilities: `git_project_id()`, `git_branch_safe()`, `git_diff_stat()`, `git_recent_commits()`, `has_changes()`
- [x] Implement security hardening: `validate_hint()` for injection detection, `wrap_untrusted()` for data tagging, stage-specific `allowed_tools` (read-only for 0,1,3; read-write for 2)

### Phase 2: Stage Implementation

- [x] Define stage prompts: port all 4 stage templates (0-populate, 1-research, 2-implement, 3-commit) with placeholder substitution (`{task_id}`, `{hint}`, `{diff}`, `{recent_commits}`, `{spec_file}`)
- [x] Implement `run_stage()`: execute single stage with model selection, success/failure detection, task_id extraction from Stage 1 output
- [x] Implement `run_stage_0()`: parse SPEC.md and create tasks idempotently using haiku model

### Phase 3: Pipeline Orchestration

- [x] Implement `run_task()`: execute stages 1-3 for a single task, pass task_id between stages, conditional Stage 3 execution
- [x] Implement `run_pipeline()`: coordinate all stages with two modes (single-task when task_id provided, iteration mode otherwise)
- [x] Add CLI interface: argparse with `task_id` (optional), `--hint/-H`, `--count/-c`, `--verbose/-v`, `--dry-run/-n`

### Phase 4: Quality & Documentation

- [ ] Add tests: unit tests for git utilities, integration tests for stages with mocked SDK responses
- [ ] Update README.md: document Python usage, installation (`pip install -e .`), CLI examples
