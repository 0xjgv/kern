# kern

Autonomous 7-stage pipeline using Python + Claude Code SDK with strict machine-readable stage contracts.

## Stack

- Python 3
- `claude-code-sdk`
- `git`

## Core Paths

- `/Users/juan/Code/0xjgv/kern/src/kern/cli.py` CLI parsing and dispatch
- `/Users/juan/Code/0xjgv/kern/src/kern/runtime.py` queue orchestration, stage sequencing, validate/fix gate
- `/Users/juan/Code/0xjgv/kern/src/kern/sdk_runner.py` SDK invocation bridge
- `/Users/juan/Code/0xjgv/kern/src/kern/stage_output.py` strict stage output parser
- `/Users/juan/Code/0xjgv/kern/src/kern/validation.py` success criteria validator
- `/Users/juan/Code/0xjgv/kern/src/kern/evaluation.py` per-attempt scoring + soft gate
- `/Users/juan/Code/0xjgv/kern/src/kern/runlog.py` run events + evaluation report persistence
- `/Users/juan/Code/0xjgv/kern/src/kern/state.py` normalized task state (`planned_files`, `success_criteria`)
- `/Users/juan/Code/0xjgv/kern/src/kern/handoff.py` append-only handoff helpers
- `/Users/juan/Code/0xjgv/kern/prompts/` stage templates `0..6`

## Runtime Artifacts

All artifacts are scoped to the invocation directory under `.kern/`:

- `handoff/task-<id>.md`
- `state/task-<id>.json`
- `reports/task-<id>.jsonl`
- `runs/<run_id>/events.jsonl`

## Output Contract

Stages `1..6` must emit:

1. `<<MACHINE>>` JSON envelope
2. `<<HANDOFF>>` block for stages `1..5` (optional for stage 6)
3. Stage-specific final `SUCCESS` line

Runtime rejects malformed output and fails fast.

## Validation/Fix Behavior

- Stage 4 writes normalized criteria to task state.
- Stage 5 output is validated against those criteria.
- On critical failures, runtime does one Stage 5 fix retry and re-validates.
- Stage 6 runs only after soft gate passes and diff exists.
- Stage 6 no longer re-validates criteria; runtime is sole gate.

## Authentication

Either:

- `claude auth` login session
- `ANTHROPIC_API_KEY`

API key is optional when CLI auth session is active.
