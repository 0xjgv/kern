from __future__ import annotations

import json
import re
from typing import Any

from .types import MachineEnvelope, StageExecution, SuccessCriterion

MACHINE_START = "<<MACHINE>>"
MACHINE_END = "<<END_MACHINE>>"
HANDOFF_START = "<<HANDOFF>>"
HANDOFF_END = "<<END_HANDOFF>>"

STAGE1_SUCCESS_RE = re.compile(r"^SUCCESS task_id=(\d+|none)(?: skip=true)?$")
STAGE_N_SUCCESS_RE = re.compile(r"^SUCCESS task_id=(\d+)$")
STAGE6_SUCCESS_RE = re.compile(r"^SUCCESS$")
EXPLICIT_FAILURE_RE = re.compile(r"(?im)^(FAILED|ERROR)\b")

CRITERION_KINDS = {
    "file_exists",
    "file_contains",
    "file_not_contains",
    "command_succeeds",
    "git_diff_includes",
}


def extract_handoff_block(output: str) -> str | None:
    return _extract_block(output, HANDOFF_START, HANDOFF_END)


def _extract_machine_block(output: str) -> str | None:
    return _extract_block(output, MACHINE_START, MACHINE_END)


def _extract_block(output: str, start_token: str, end_token: str) -> str | None:
    start = output.find(start_token)
    end = output.find(end_token)
    if start == -1 or end == -1 or end <= start:
        return None
    content = output[start + len(start_token) : end].strip()
    return content or None


def parse_stage_output(output: str, stage_number: int) -> StageExecution:
    if stage_number == 0:
        if _has_explicit_failure(output):
            return _failed(output, "Stage 0 output indicates failure")
        parsed_task_id, parsed_queue_empty, parsed_skip = None, False, False
    else:
        final_line = _last_nonempty_line(output)
        if final_line is None:
            return _failed(output, "Stage output is empty")
        success_parse = _parse_success_line(final_line, stage_number)
        if success_parse is None:
            return _failed(output, f"Invalid SUCCESS line for stage {stage_number}: {final_line!r}")
        parsed_task_id, parsed_queue_empty, parsed_skip = success_parse

    machine: MachineEnvelope | None = None
    machine_block = _extract_machine_block(output)
    if stage_number >= 1:
        if machine_block is None:
            return _failed(output, f"Missing {MACHINE_START} block for stage {stage_number}")
        machine, error = _parse_machine_envelope(machine_block)
        if error:
            return _failed(output, error)
        if machine.stage != stage_number:
            return _failed(output, f"Machine stage mismatch: expected {stage_number}, got {machine.stage}")
        if machine.status != "success":
            return _failed(output, f"Machine status must be 'success', got {machine.status!r}")
        cross_error = _cross_validate_machine(
            stage_number=stage_number,
            machine=machine,
            task_id=parsed_task_id,
            queue_empty=parsed_queue_empty,
            skip=parsed_skip,
        )
        if cross_error:
            return _failed(output, cross_error)

    handoff_block = extract_handoff_block(output)
    if 1 <= stage_number <= 5 and not handoff_block:
        return _failed(output, f"Missing {HANDOFF_START} block for stage {stage_number}")

    effective_task_id = parsed_task_id
    if stage_number == 6 and machine is not None and machine.task_id is not None:
        effective_task_id = machine.task_id

    return StageExecution(
        raw_output=output,
        success=True,
        task_id=effective_task_id,
        skip=parsed_skip,
        queue_empty=parsed_queue_empty,
        handoff_block=handoff_block,
        machine=machine,
        metadata=machine.metadata if machine else None,
    )


def _parse_success_line(line: str, stage_number: int) -> tuple[int | None, bool, bool] | None:
    if stage_number == 1:
        match = STAGE1_SUCCESS_RE.fullmatch(line)
        if not match:
            return None
        task_raw = match.group(1)
        task_id = None if task_raw == "none" else int(task_raw)
        queue_empty = task_id is None
        skip = " skip=true" in line
        return task_id, queue_empty, skip

    if stage_number in {2, 3, 4, 5}:
        match = STAGE_N_SUCCESS_RE.fullmatch(line)
        if not match:
            return None
        return int(match.group(1)), False, False

    if stage_number == 6:
        return (None, False, False) if STAGE6_SUCCESS_RE.fullmatch(line) else None

    return None


def _has_explicit_failure(output: str) -> bool:
    return bool(EXPLICIT_FAILURE_RE.search(output))


def _parse_machine_envelope(machine_block: str) -> tuple[MachineEnvelope | None, str | None]:
    if "\n" in machine_block.strip():
        return None, "Machine block must contain exactly one JSON line"
    try:
        payload = json.loads(machine_block)
    except json.JSONDecodeError as exc:
        return None, f"Invalid machine JSON: {exc}"

    if not isinstance(payload, dict):
        return None, "Machine block must be a JSON object"

    required = {"stage", "status", "task_id", "queue_empty", "skip", "summary"}
    missing = required - set(payload)
    if missing:
        names = ", ".join(sorted(missing))
        return None, f"Machine block missing fields: {names}"

    stage = payload.get("stage")
    status = payload.get("status")
    task_id = payload.get("task_id")
    queue_empty = payload.get("queue_empty")
    skip = payload.get("skip")
    summary = payload.get("summary")
    metadata = payload.get("metadata")
    planned_files_raw = payload.get("planned_files")
    criteria_raw = payload.get("criteria")

    if isinstance(stage, str) and stage.isdigit():
        stage = int(stage)
    if not isinstance(stage, int):
        return None, "Machine field 'stage' must be an integer"
    if isinstance(status, str):
        status = status.strip().lower()
    if status not in {"success", "failed"}:
        return None, "Machine field 'status' must be 'success' or 'failed'"
    if isinstance(task_id, str):
        lowered = task_id.strip().lower()
        if lowered.isdigit():
            task_id = int(lowered)
        elif lowered in {"", "none", "null"}:
            task_id = None
    if task_id is not None and not isinstance(task_id, int):
        return None, "Machine field 'task_id' must be integer or null"
    if isinstance(queue_empty, str):
        lowered = queue_empty.strip().lower()
        if lowered == "true":
            queue_empty = True
        elif lowered == "false":
            queue_empty = False
    if not isinstance(queue_empty, bool):
        return None, "Machine field 'queue_empty' must be boolean"
    if isinstance(skip, str):
        lowered = skip.strip().lower()
        if lowered == "true":
            skip = True
        elif lowered == "false":
            skip = False
    if not isinstance(skip, bool):
        return None, "Machine field 'skip' must be boolean"
    if not isinstance(summary, str) or not summary.strip():
        return None, "Machine field 'summary' must be a non-empty string"
    if metadata is not None and not isinstance(metadata, dict):
        return None, "Machine field 'metadata' must be an object when present"

    planned_files: list[str] | None = None
    if planned_files_raw is not None:
        if not isinstance(planned_files_raw, list) or any(not isinstance(item, str) for item in planned_files_raw):
            return None, "Machine field 'planned_files' must be an array of strings"
        planned_files = [item.strip() for item in planned_files_raw if item and item.strip()]

    criteria: list[SuccessCriterion] | None = None
    if criteria_raw is not None:
        if not isinstance(criteria_raw, list):
            return None, "Machine field 'criteria' must be an array"
        parsed_criteria: list[SuccessCriterion] = []
        for index, item in enumerate(criteria_raw):
            if not isinstance(item, dict):
                return None, f"Machine criteria[{index}] must be an object"
            kind = item.get("kind")
            value = item.get("value")
            if not isinstance(kind, str) or kind not in CRITERION_KINDS:
                return None, f"Machine criteria[{index}].kind is invalid"
            if not isinstance(value, str) or not value.strip():
                return None, f"Machine criteria[{index}].value must be non-empty string"
            parsed_criteria.append(SuccessCriterion(kind=kind, value=value.strip()))
        criteria = parsed_criteria

    return (
        MachineEnvelope(
            stage=stage,
            status=status,
            task_id=task_id,
            queue_empty=queue_empty,
            skip=skip,
            summary=summary.strip(),
            criteria=criteria,
            planned_files=planned_files,
            metadata=metadata,
        ),
        None,
    )


def _cross_validate_machine(
    stage_number: int,
    machine: MachineEnvelope,
    task_id: int | None,
    queue_empty: bool,
    skip: bool,
) -> str | None:
    if stage_number == 1:
        if machine.queue_empty != queue_empty:
            return f"Machine queue_empty mismatch: expected {queue_empty}, got {machine.queue_empty}"
        if machine.skip != skip:
            return f"Machine skip mismatch: expected {skip}, got {machine.skip}"
        if machine.task_id != task_id:
            return f"Machine task_id mismatch: expected {task_id}, got {machine.task_id}"
        if queue_empty and task_id is not None:
            return "Stage 1 queue-empty output must have task_id=null"
        if not queue_empty and task_id is None:
            return "Stage 1 selected-task output must have task_id integer"
        return None

    if stage_number in {2, 3, 4, 5}:
        if machine.queue_empty != queue_empty:
            return f"Machine queue_empty mismatch: expected {queue_empty}, got {machine.queue_empty}"
        if machine.skip != skip:
            return f"Machine skip mismatch: expected {skip}, got {machine.skip}"
        if machine.task_id != task_id:
            return f"Machine task_id mismatch: expected {task_id}, got {machine.task_id}"
        if task_id is None:
            return f"Stage {stage_number} requires task_id in SUCCESS line"
        if queue_empty:
            return f"Stage {stage_number} cannot set queue_empty=true"
        if skip:
            return f"Stage {stage_number} cannot set skip=true"
        return None

    if stage_number == 6:
        return None

    return None


def _last_nonempty_line(output: str) -> str | None:
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _failed(output: str, reason: str) -> StageExecution:
    return StageExecution(
        raw_output=output,
        success=False,
        task_id=None,
        skip=False,
        queue_empty=False,
        handoff_block=None,
        machine=None,
        metadata=None,
        error=reason,
    )
