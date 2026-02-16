from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import random
import re
import subprocess
import sys
from typing import Iterable

from .evaluation import evaluate_iteration
from .handoff import (
    append_evaluation_result,
    append_fix_context,
    append_handoff_block,
    append_validation_result,
    ensure_handoff_dir,
    handoff_path,
    init_handoff_file,
)
from .logging import debug, die, log
from .prompting import (
    collect_diff_stat,
    collect_recent_commits,
    parse_prompt_template,
    render_prompt,
    validate_hint,
    wrap_untrusted,
)
from .runlog import RunLogger
from .sdk_runner import ClaudeSdkRunner
from .stages import stage_specs
from .state import ensure_state_dir, load_planned_files, load_success_criteria, update_task_state_from_machine
from .types import (
    IterationEvaluation,
    RunContext,
    StageExecution,
    StageRunner,
    StageSpec,
    SuccessCriterion,
    ValidationResult,
    Validator,
)
from .validation import SuccessCriteriaValidator

SPEC_FILE = "SPEC.md"


class NoTaskAvailable(Exception):
    pass


class TaskFailed(Exception):
    pass


def run(
    task_id: int | None,
    max_tasks: int,
    hint: str,
    dry_run: bool,
    verbose: bool,
    *,
    stage_runner: StageRunner | None = None,
    validator: Validator | None = None,
    run_dir: Path | None = None,
) -> int:
    try:
        validate_hint(hint)
    except ValueError as exc:
        return die(1, str(exc))

    active_run_dir = (run_dir or Path.cwd()).resolve()
    kern_dir = active_run_dir / ".kern"
    run_id = _new_run_id()
    run_logger = RunLogger(kern_dir, run_id)
    handoff_dir = kern_dir / "handoff"
    state_dir = kern_dir / "state"
    ctx = RunContext(
        run_dir=active_run_dir,
        kern_dir=kern_dir,
        handoff_dir=handoff_dir,
        task_id=task_id,
        hint=hint,
        max_tasks=max_tasks,
        dry_run=dry_run,
        verbose=verbose,
        run_id=run_id,
        run_log_file=run_logger.events_file,
        report_dir=run_logger.reports_dir,
        state_dir=state_dir,
    )

    if stage_runner is None:
        env = {
            "CLAUDE_CODE_TASK_LIST_ID": _task_list_id(active_run_dir),
            "CLAUDE_CODE_ENABLE_TASKS": "true",
        }
        stage_runner = ClaudeSdkRunner(env=env, verbose=verbose)
    if validator is None:
        validator = SuccessCriteriaValidator()

    return asyncio.run(_run(ctx, stage_runner, validator, run_logger))


async def _run(ctx: RunContext, stage_runner: StageRunner, validator: Validator, run_logger: RunLogger) -> int:
    try:
        specs = stage_specs(_resolve_kern_home(ctx.run_dir) / "prompts")
    except Exception as exc:  # noqa: BLE001
        return die(1, f"Unable to resolve prompts directory: {exc}")

    if ctx.task_id is not None:
        try:
            await _run_task(ctx, specs, stage_runner, validator, run_logger)
            return 0
        except NoTaskAvailable:
            return die(1, f"Task {ctx.task_id} failed")
        except TaskFailed as exc:
            return die(1, str(exc))

    if ctx.dry_run:
        _print_dry_run_queue(ctx.run_dir, ctx.max_tasks)
        return 0

    try:
        await _run_stage(ctx, specs[0], stage_runner, run_logger=run_logger)
    except TaskFailed as exc:
        return die(1, f"Failed to populate task queue: {exc}")

    task_count = 0
    while True:
        if task_count >= ctx.max_tasks:
            log(f"Reached max tasks limit ({ctx.max_tasks})")
            break
        ctx.task_id = None
        try:
            await _run_task(ctx, specs, stage_runner, validator, run_logger)
            task_count += 1
        except NoTaskAvailable:
            break
        except TaskFailed as exc:
            current = ctx.task_id if ctx.task_id is not None else "unknown"
            return die(1, f"Task {current} failed: {exc}")

    if task_count == 0:
        log("No pending tasks in queue")
    else:
        log(f"Completed {task_count} task(s)")
    return 0


async def _run_task(
    ctx: RunContext,
    specs: dict[int, StageSpec],
    stage_runner: StageRunner,
    validator: Validator,
    run_logger: RunLogger,
) -> None:
    if ctx.dry_run:
        for number in range(1, 7):
            await _run_stage(ctx, specs[number], stage_runner, run_logger=run_logger)
        return

    if ctx.task_id is None:
        log("Selecting next task...")

    first = await _run_stage(ctx, specs[1], stage_runner, run_logger=run_logger)
    if first.queue_empty or ctx.task_id is None:
        log("No more tasks in queue")
        raise NoTaskAvailable

    ensure_handoff_dir(ctx.handoff_dir)
    ensure_state_dir(ctx.state_dir)
    handoff_file = handoff_path(ctx.handoff_dir, ctx.task_id)
    init_handoff_file(handoff_file, ctx.task_id, ctx.hint, ctx.run_dir)
    append_handoff_block(handoff_file, first.handoff_block, required=True)
    update_task_state_from_machine(ctx.state_dir, ctx.task_id, first.machine)

    log(f"Executing task: {ctx.task_id}")
    if first.skip:
        log(f"Task {ctx.task_id} already complete, skipping implementation")
        return

    for stage_number in (2, 3, 4):
        result = await _run_stage(
            ctx,
            specs[stage_number],
            stage_runner,
            run_logger=run_logger,
            handoff_file=handoff_file,
        )
        append_handoff_block(handoff_file, result.handoff_block, required=True)
        update_task_state_from_machine(ctx.state_dir, ctx.task_id, result.machine)

    criteria = load_success_criteria(ctx.state_dir, ctx.task_id)
    if not criteria:
        raise TaskFailed("Stage 4 must provide normalized criteria in machine block")
    planned_files = load_planned_files(ctx.state_dir, ctx.task_id)

    implement_result = await _run_stage(
        ctx,
        specs[5],
        stage_runner,
        run_logger=run_logger,
        handoff_file=handoff_file,
    )
    append_handoff_block(handoff_file, implement_result.handoff_block, required=True)
    update_task_state_from_machine(ctx.state_dir, ctx.task_id, implement_result.machine)

    evaluation, validation_result = _validate_and_evaluate(
        ctx=ctx,
        task_id=ctx.task_id,
        attempt=1,
        handoff_file=handoff_file,
        validator=validator,
        run_logger=run_logger,
        criteria=criteria,
        planned_files=planned_files,
    )

    if not evaluation.passed_soft_gate:
        if ctx.max_fix_attempts < 1:
            raise TaskFailed("Validation failed and fix attempts are disabled")
        append_fix_context(handoff_file, validation_result)
        fix_hint = _build_fix_hint(ctx.hint, validation_result, evaluation)
        retry_result = await _run_stage(
            ctx,
            specs[5],
            stage_runner,
            run_logger=run_logger,
            handoff_file=handoff_file,
            hint_override=fix_hint,
        )
        append_handoff_block(handoff_file, retry_result.handoff_block, required=True)
        update_task_state_from_machine(ctx.state_dir, ctx.task_id, retry_result.machine)

        evaluation, validation_result = _validate_and_evaluate(
            ctx=ctx,
            task_id=ctx.task_id,
            attempt=2,
            handoff_file=handoff_file,
            validator=validator,
            run_logger=run_logger,
            criteria=criteria,
            planned_files=planned_files,
        )
        if not evaluation.passed_soft_gate:
            raise TaskFailed(
                f"Validation failed after 1 fix attempt: {', '.join(evaluation.critical_failures) or 'unknown error'}"
            )

    if _git_has_changes(ctx.run_dir):
        commit_result = await _run_stage(
            ctx,
            specs[6],
            stage_runner,
            run_logger=run_logger,
            handoff_file=handoff_file,
        )
        append_handoff_block(handoff_file, commit_result.handoff_block, required=False)
    else:
        log("No changes to commit")

    log(f"Task {ctx.task_id} completed")


def _validate_and_evaluate(
    *,
    ctx: RunContext,
    task_id: int,
    attempt: int,
    handoff_file: Path,
    validator: Validator,
    run_logger: RunLogger,
    criteria: list[SuccessCriterion],
    planned_files: list[str],
) -> tuple[IterationEvaluation, ValidationResult]:
    validation = validator.validate(task_id, ctx.run_dir, handoff_file, criteria=criteria)
    append_validation_result(handoff_file, validation, attempt=attempt)

    previous_score = run_logger.previous_score(task_id)
    evaluation = evaluate_iteration(
        task_id=task_id,
        attempt=attempt,
        validation=validation,
        changed_files=_git_changed_files(ctx.run_dir),
        planned_files=planned_files,
        contract_failures=[],
        previous_score=previous_score,
    )
    append_evaluation_result(handoff_file, evaluation)
    run_logger.append_evaluation(evaluation)
    return evaluation, validation


async def _run_stage(
    ctx: RunContext,
    stage_spec: StageSpec,
    stage_runner: StageRunner,
    *,
    run_logger: RunLogger,
    handoff_file: Path | None = None,
    hint_override: str | None = None,
) -> StageExecution:
    log(f"Stage {stage_spec.number}: {stage_spec.name}")

    template = parse_prompt_template(stage_spec.prompt_path)
    model = template.model or stage_spec.default_model
    if ctx.dry_run:
        log(f"[DRY-RUN] Would run: claude --model {model}")
        return StageExecution(raw_output="", success=True, task_id=ctx.task_id, skip=False)

    prompt = render_prompt(
        template.body,
        _substitutions(
            run_dir=ctx.run_dir,
            task_id=ctx.task_id,
            hint=hint_override if hint_override is not None else ctx.hint,
            handoff_file=handoff_file,
        ),
    )

    started = datetime.now(timezone.utc)
    execution = await stage_runner.run_stage(stage_spec, prompt, ctx.run_dir, model)
    ended = datetime.now(timezone.utc)
    event_task_id = execution.task_id if execution.task_id is not None else ctx.task_id
    run_logger.log_stage_event(
        task_id=event_task_id,
        stage=stage_spec,
        model=model,
        started_at=started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ended_at=ended.strftime("%Y-%m-%dT%H:%M:%SZ"),
        duration_ms=max(0, int((ended - started).total_seconds() * 1000)),
        execution=execution,
    )

    if not execution.success:
        if execution.error:
            raise TaskFailed(execution.error)
        raise TaskFailed(execution.raw_output)

    if stage_spec.number == 1:
        if execution.queue_empty:
            ctx.task_id = None
        elif execution.task_id is not None:
            ctx.task_id = execution.task_id
            debug(ctx.verbose, f"Stage 1 selected task: {ctx.task_id}")
        else:
            raise TaskFailed("Stage 1 must return task_id=<ID> or task_id=none")
        if execution.skip:
            debug(ctx.verbose, f"Task {ctx.task_id} already complete, will skip")
    elif stage_spec.number in {2, 3, 4, 5}:
        if ctx.task_id is None:
            raise TaskFailed(f"Stage {stage_spec.number} cannot run without active task_id")
        if execution.task_id != ctx.task_id:
            raise TaskFailed(
                f"Stage {stage_spec.number} returned task_id={execution.task_id}, expected {ctx.task_id}"
            )
    return execution


def _substitutions(run_dir: Path, task_id: int | None, hint: str, handoff_file: Path | None) -> dict[str, str]:
    return {
        "TASK_ID": "" if task_id is None else str(task_id),
        "HINT": wrap_untrusted("hint", hint),
        "DIFF": collect_diff_stat(run_dir),
        "RECENT_COMMITS": collect_recent_commits(run_dir),
        "SPEC_FILE": SPEC_FILE,
        "HANDOFF_FILE": "" if handoff_file is None else str(handoff_file),
    }


def _task_list_id(run_dir: Path) -> str:
    return f"{_git_project_id(run_dir)}-{_git_branch_safe(run_dir)}"


def _git_project_id(run_dir: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=run_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).name
    return run_dir.name


def _git_branch_safe(run_dir: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=run_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip().replace("/", "-") or "unknown"


def _git_has_changes(run_dir: Path) -> bool:
    diff = subprocess.run(["git", "diff", "--quiet"], cwd=run_dir, check=False)
    cached = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=run_dir, check=False)
    return diff.returncode != 0 or cached.returncode != 0


def _git_changed_files(run_dir: Path) -> list[str]:
    names: list[str] = []
    for command in (["git", "diff", "--name-only"], ["git", "diff", "--cached", "--name-only"]):
        completed = subprocess.run(
            command,
            cwd=run_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            names.extend(line.strip() for line in completed.stdout.splitlines() if line.strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return deduped


def _extract_tasks(spec_file: Path) -> Iterable[tuple[int, str, str]]:
    pattern = re.compile(r"^\s*-\s\[(~| )\]\s(.*)$")
    for index, line in enumerate(spec_file.read_text(encoding="utf-8").splitlines(), start=1):
        match = pattern.match(line)
        if match:
            yield index, match.group(1), match.group(2)


def _print_dry_run_queue(run_dir: Path, max_tasks: int) -> None:
    log(f"[DRY-RUN] Would process up to {max_tasks} tasks from {SPEC_FILE}:")
    spec_path = run_dir / SPEC_FILE
    if not spec_path.exists():
        log(f"  - Missing {SPEC_FILE}")
        return
    for line_no, _, desc in list(_extract_tasks(spec_path))[:max_tasks]:
        log(f"  - Line {line_no}: {desc}")


def _build_fix_hint(base_hint: str, validation: ValidationResult, evaluation: IterationEvaluation) -> str:
    summary_lines = ["Fix critical validation failures before commit."]
    for check in validation.checks:
        if not check.passed and check.kind in {"file_exists", "file_contains", "file_not_contains", "command_succeeds"}:
            summary_lines.append(f"{check.criterion} :: {check.details}")
    for advisory in evaluation.advisories:
        summary_lines.append(f"Advisory: {advisory}")
    merged = "\n".join(summary_lines)
    if base_hint.strip():
        return f"{base_hint}\n{merged}"
    return merged


def _new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{os.getpid()}-{random.randint(1000, 9999)}"


def _resolve_kern_home(run_dir: Path) -> Path:
    candidates: list[Path] = []
    env_home = os.environ.get("KERN_HOME")
    if env_home:
        candidates.append(Path(env_home).expanduser())
    candidates.append(run_dir)
    candidates.append(Path(__file__).resolve().parents[2])

    argv0 = Path(sys.argv[0]).expanduser()
    if argv0.exists():
        resolved = argv0.resolve()
        if len(resolved.parents) >= 3:
            candidates.append(resolved.parents[2])

    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "kern"
    candidates.append(data_home)

    for candidate in candidates:
        prompts = candidate / "prompts"
        if (prompts / "0_populate_queue.md").exists() and (prompts / "6_review_commit.md").exists():
            return candidate
    raise RuntimeError("Could not locate kern home with prompts/")
