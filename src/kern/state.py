from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import MachineEnvelope, SuccessCriterion

CRITERION_KINDS = {
    "file_exists",
    "file_contains",
    "file_not_contains",
    "command_succeeds",
    "git_diff_includes",
}


def ensure_state_dir(state_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)


def task_state_path(state_dir: Path, task_id: int) -> Path:
    return state_dir / f"task-{task_id}.json"


def load_task_state(state_dir: Path, task_id: int) -> dict[str, Any]:
    path = task_state_path(state_dir, task_id)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def save_task_state(state_dir: Path, task_id: int, payload: dict[str, Any]) -> None:
    ensure_state_dir(state_dir)
    path = task_state_path(state_dir, task_id)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_task_state_from_machine(state_dir: Path, task_id: int, machine: MachineEnvelope | None) -> None:
    if machine is None:
        return
    payload = load_task_state(state_dir, task_id)
    payload["task_id"] = task_id

    if machine.stage == 3 and machine.planned_files is not None:
        payload["planned_files"] = machine.planned_files

    if machine.stage == 4 and machine.criteria is not None:
        payload["success_criteria"] = [
            {"kind": criterion.kind, "value": criterion.value} for criterion in machine.criteria
        ]

    if machine.metadata is not None:
        payload.setdefault("stage_metadata", {})[str(machine.stage)] = machine.metadata

    save_task_state(state_dir, task_id, payload)


def load_success_criteria(state_dir: Path, task_id: int) -> list[SuccessCriterion] | None:
    payload = load_task_state(state_dir, task_id)
    raw = payload.get("success_criteria")
    if not isinstance(raw, list):
        return None
    criteria: list[SuccessCriterion] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        value = item.get("value")
        if isinstance(kind, str) and kind in CRITERION_KINDS and isinstance(value, str):
            criteria.append(SuccessCriterion(kind=kind, value=value))
    return criteria or None


def load_planned_files(state_dir: Path, task_id: int) -> list[str]:
    payload = load_task_state(state_dir, task_id)
    raw = payload.get("planned_files")
    if not isinstance(raw, list):
        return []
    values = [item.strip() for item in raw if isinstance(item, str) and item.strip()]
    return values
