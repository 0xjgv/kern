from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import kern.runtime as runtime
from kern.types import (
    MachineEnvelope,
    StageExecution,
    StageSpec,
    SuccessCriterion,
    ValidationCheckResult,
    ValidationResult,
)


@dataclass
class FakeRunner:
    stages: dict[int, list[StageExecution]]

    def __post_init__(self) -> None:
        self.calls: list[int] = []

    async def run_stage(self, stage: StageSpec, prompt: str, cwd: Path, model: str) -> StageExecution:
        self.calls.append(stage.number)
        queue = self.stages.get(stage.number)
        if not queue:
            raise AssertionError(f"No fake output for stage {stage.number}")
        return queue.pop(0)


@dataclass
class FakeValidator:
    results: list[ValidationResult]

    def __post_init__(self) -> None:
        self.calls = 0

    def validate(self, task_id: int, run_dir: Path, handoff_file: Path, criteria=None) -> ValidationResult:
        self.calls += 1
        if not self.results:
            return ValidationResult(
                passed=True,
                checks=[ValidationCheckResult("success_criteria_present", "success_criteria_present", True, "none")],
            )
        return self.results.pop(0)


def stage_output(
    raw: str,
    *,
    task_id: int | None = None,
    skip: bool = False,
    queue_empty: bool = False,
    handoff: str | None = None,
    stage: int = 1,
    criteria=None,
    planned_files=None,
) -> StageExecution:
    return StageExecution(
        raw_output=raw,
        success=True,
        task_id=task_id,
        skip=skip,
        queue_empty=queue_empty,
        handoff_block=handoff,
        machine=MachineEnvelope(
            stage=stage,
            status="success",
            task_id=task_id,
            queue_empty=queue_empty,
            skip=skip,
            summary="ok",
            criteria=criteria,
            planned_files=planned_files,
            metadata={},
        ),
    )


def test_queue_mode_exits_when_no_task(tmp_path: Path) -> None:
    spec = tmp_path / "SPEC.md"
    spec.write_text("# Tasks\n- [ ] task\n", encoding="utf-8")
    runner = FakeRunner(
        stages={
            0: [stage_output("SUCCESS created=1 existing=0")],
            1: [stage_output("SUCCESS task_id=none", task_id=None, queue_empty=True, stage=1)],
        }
    )
    code = runtime.run(
        task_id=None,
        max_tasks=5,
        hint="",
        dry_run=False,
        verbose=False,
        stage_runner=runner,
        validator=FakeValidator([]),
        run_dir=tmp_path,
    )
    assert code == 0
    assert runner.calls == [0, 1]


def test_skip_short_circuits_after_research(tmp_path: Path) -> None:
    (tmp_path / "SPEC.md").write_text("# Tasks\n- [ ] task\n", encoding="utf-8")
    runner = FakeRunner(
        stages={
            1: [
                stage_output(
                    "SUCCESS task_id=7 skip=true",
                    task_id=7,
                    skip=True,
                    handoff="## Research\n- Summary: done",
                    stage=1,
                )
            ]
        }
    )
    code = runtime.run(
        task_id=7,
        max_tasks=1,
        hint="",
        dry_run=False,
        verbose=False,
        stage_runner=runner,
        validator=FakeValidator([]),
        run_dir=tmp_path,
    )
    handoff = tmp_path / ".kern" / "handoff" / "task-7.md"
    assert code == 0
    assert runner.calls == [1]
    assert handoff.exists()
    content = handoff.read_text(encoding="utf-8")
    assert "## Research" in content
    assert "## Plan" not in content


def test_validate_fix_retry_then_commit(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "SPEC.md").write_text("# Tasks\n- [ ] task\n", encoding="utf-8")
    monkeypatch.setattr(runtime, "_git_has_changes", lambda _: True)

    fail = ValidationResult(
        passed=False,
        checks=[ValidationCheckResult("file_exists: foo.txt", "file_exists", False, "missing")],
    )
    success = ValidationResult(
        passed=True,
        checks=[ValidationCheckResult("file_exists: foo.txt", "file_exists", True, "ok")],
    )
    validator = FakeValidator([fail, success])
    runner = FakeRunner(
        stages={
            1: [stage_output("SUCCESS task_id=5", task_id=5, handoff="## Research\n- Summary: r", stage=1)],
            2: [stage_output("SUCCESS task_id=5", task_id=5, handoff="## Design\n- Decisions: d", stage=2)],
            3: [
                stage_output(
                    "SUCCESS task_id=5",
                    task_id=5,
                    handoff="## Structure\n- Files: s",
                    stage=3,
                    planned_files=["README.md"],
                )
            ],
            4: [
                stage_output(
                    "SUCCESS task_id=5",
                    task_id=5,
                    handoff="## Plan\n- Steps: p",
                    stage=4,
                    criteria=[SuccessCriterion(kind="file_exists", value="README.md")],
                )
            ],
            5: [
                stage_output("SUCCESS task_id=5", task_id=5, handoff="## Implement\n- Summary: first", stage=5),
                stage_output("SUCCESS task_id=5", task_id=5, handoff="## Implement\n- Summary: retry", stage=5),
            ],
            6: [stage_output("SUCCESS", handoff="## Review & Commit\n- Commit: x", stage=6)],
        }
    )
    code = runtime.run(
        task_id=5,
        max_tasks=1,
        hint="",
        dry_run=False,
        verbose=False,
        stage_runner=runner,
        validator=validator,
        run_dir=tmp_path,
    )
    assert code == 0
    assert validator.calls == 2
    assert runner.calls == [1, 2, 3, 4, 5, 5, 6]
