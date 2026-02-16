from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .types import IterationEvaluation, ValidationResult


def handoff_path(handoff_dir: Path, task_id: int) -> Path:
    return handoff_dir / f"task-{task_id}.md"


def ensure_handoff_dir(handoff_dir: Path) -> None:
    handoff_dir.mkdir(parents=True, exist_ok=True)


def init_handoff_file(file_path: Path, task_id: int, hint: str, run_dir: Path) -> None:
    if file_path.exists():
        return
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = "\n".join(
        [
            "# Task Handoff",
            f"Task ID: {task_id}",
            f"Hint: {hint}",
            f"Created: {created}",
            f"Run Directory: {run_dir}",
            "",
        ]
    )
    file_path.write_text(header, encoding="utf-8")


def append_handoff_block(file_path: Path, block: str | None, required: bool) -> None:
    if not block:
        if required:
            raise RuntimeError("Missing handoff block in stage output")
        return
    with file_path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n{block.strip()}\n")


def append_validation_result(file_path: Path, result: ValidationResult, attempt: int) -> None:
    status = "PASSED" if result.passed else "FAILED"
    lines = [
        "## Validation",
        f"- Attempt: {attempt}",
        f"- Status: {status}",
    ]
    for check in result.checks:
        prefix = "PASS" if check.passed else "FAIL"
        lines.append(f"- {prefix}: {check.criterion} :: {check.details}")
    with file_path.open("a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(lines) + "\n")


def append_evaluation_result(file_path: Path, evaluation: IterationEvaluation) -> None:
    status = "PASSED" if evaluation.passed_soft_gate else "FAILED"
    lines = [
        "## Evaluation",
        f"- Attempt: {evaluation.attempt}",
        f"- Score: {evaluation.score}",
        f"- Soft gate: {status}",
    ]
    if evaluation.critical_failures:
        lines.append("- Critical failures:")
        for item in evaluation.critical_failures:
            lines.append(f"  - {item}")
    if evaluation.advisories:
        lines.append("- Advisories:")
        for item in evaluation.advisories:
            lines.append(f"  - {item}")
    with file_path.open("a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(lines) + "\n")


def append_fix_context(file_path: Path, result: ValidationResult) -> None:
    failed = [check for check in result.checks if not check.passed]
    lines = [
        "## Fix Context",
        "- Previous validation failed. Apply minimal changes and re-run validation.",
    ]
    for check in failed:
        lines.append(f"- Failed criterion: {check.criterion}")
        lines.append(f"- Details: {check.details}")
    with file_path.open("a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(lines) + "\n")
