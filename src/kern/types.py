from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol


PermissionMode = Literal["default", "bypassPermissions"]
CriterionKind = Literal[
    "file_exists",
    "file_contains",
    "file_not_contains",
    "command_succeeds",
    "git_diff_includes",
]


@dataclass(frozen=True)
class StageSpec:
    number: int
    name: str
    prompt_path: Path
    default_model: str
    allowed_tools: list[str] | None
    permission_mode: PermissionMode


@dataclass
class StageExecution:
    raw_output: str
    success: bool
    task_id: int | None
    skip: bool
    queue_empty: bool = False
    handoff_block: str | None = None
    machine: MachineEnvelope | None = None
    metadata: dict[str, Any] | None = None
    error: str | None = None
    usage: dict[str, Any] | None = None
    total_cost_usd: float | None = None


@dataclass(frozen=True)
class SuccessCriterion:
    kind: CriterionKind
    value: str


@dataclass(frozen=True)
class MachineEnvelope:
    stage: int
    status: Literal["success", "failed"]
    task_id: int | None
    queue_empty: bool
    skip: bool
    summary: str
    criteria: list[SuccessCriterion] | None = None
    planned_files: list[str] | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class IterationEvaluation:
    task_id: int
    attempt: int
    score: int
    critical_failures: list[str]
    advisories: list[str]
    passed_soft_gate: bool
    timestamp_utc: str


@dataclass
class RunContext:
    run_dir: Path
    kern_dir: Path
    handoff_dir: Path
    task_id: int | None
    hint: str
    max_tasks: int
    dry_run: bool
    verbose: bool
    run_id: str
    run_log_file: Path
    report_dir: Path
    state_dir: Path
    max_fix_attempts: int = 1


@dataclass
class ValidationCheckResult:
    criterion: str
    kind: str
    passed: bool
    details: str


@dataclass
class ValidationResult:
    passed: bool
    checks: list[ValidationCheckResult]

    def summary(self) -> str:
        if self.passed:
            return "validation passed"
        failed = [check.criterion for check in self.checks if not check.passed]
        if not failed:
            return "validation failed"
        return f"failed criteria: {', '.join(failed)}"


class StageRunner(Protocol):
    async def run_stage(self, stage: StageSpec, prompt: str, cwd: Path, model: str) -> StageExecution:
        ...


class Validator(Protocol):
    def validate(
        self,
        task_id: int,
        run_dir: Path,
        handoff_file: Path,
        criteria: list[SuccessCriterion] | None = None,
    ) -> ValidationResult:
        ...
