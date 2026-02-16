from kern.evaluation import evaluate_iteration
from kern.types import ValidationCheckResult, ValidationResult


def test_evaluation_marks_critical_failures() -> None:
    validation = ValidationResult(
        passed=False,
        checks=[
            ValidationCheckResult("file_exists: README.md", "file_exists", False, "missing"),
            ValidationCheckResult("git_diff_includes: README.md", "git_diff_includes", False, "missing in diff"),
        ],
    )
    result = evaluate_iteration(
        task_id=9,
        attempt=1,
        validation=validation,
        changed_files=["README.md"],
        planned_files=["README.md"],
        previous_score=None,
    )
    assert result.passed_soft_gate is False
    assert any("file_exists" in item for item in result.critical_failures)
    assert any("git_diff_includes" in item for item in result.advisories)


def test_evaluation_reports_score_regression() -> None:
    validation = ValidationResult(
        passed=False,
        checks=[ValidationCheckResult("command_succeeds: pytest -q", "command_succeeds", False, "exit=1")],
    )
    result = evaluate_iteration(
        task_id=1,
        attempt=2,
        validation=validation,
        changed_files=["src/a.py", "src/b.py"],
        planned_files=["src/a.py"],
        previous_score=95,
    )
    assert result.score < 80
    assert any("score regression" in item for item in result.advisories)
