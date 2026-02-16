from __future__ import annotations

from datetime import datetime, timezone

from .types import IterationEvaluation, ValidationResult

CRITICAL_KINDS = {
    "file_exists",
    "file_contains",
    "file_not_contains",
    "command_succeeds",
}


def evaluate_iteration(
    *,
    task_id: int,
    attempt: int,
    validation: ValidationResult,
    changed_files: list[str],
    planned_files: list[str],
    contract_failures: list[str] | None = None,
    previous_score: int | None = None,
) -> IterationEvaluation:
    contract_failures = contract_failures or []
    critical_failures: list[str] = []
    advisories: list[str] = []

    critical_checks = [check for check in validation.checks if check.kind in CRITICAL_KINDS]
    if critical_checks:
        critical_passed = sum(1 for check in critical_checks if check.passed)
        critical_points = int(round(50 * (critical_passed / len(critical_checks))))
    else:
        critical_points = 50
    for check in critical_checks:
        if not check.passed:
            critical_failures.append(check.criterion)

    command_checks = [check for check in validation.checks if check.kind == "command_succeeds"]
    if command_checks:
        command_passed = sum(1 for check in command_checks if check.passed)
        command_points = int(round(20 * (command_passed / len(command_checks))))
    else:
        command_points = 20

    scope_points, scope_advisories = _scope_score(changed_files, planned_files)
    advisories.extend(scope_advisories)

    contract_points = 10
    for failure in contract_failures:
        critical_failures.append(f"contract: {failure}")
    if contract_failures:
        contract_points = 0

    for check in validation.checks:
        if check.kind == "git_diff_includes" and not check.passed:
            advisories.append(f"git_diff_includes unmet: {check.details}")

    score = max(0, min(100, critical_points + scope_points + command_points + contract_points))
    if previous_score is not None and previous_score - score >= 15:
        advisories.append(f"score regression: previous={previous_score} current={score}")

    return IterationEvaluation(
        task_id=task_id,
        attempt=attempt,
        score=score,
        critical_failures=critical_failures,
        advisories=advisories,
        passed_soft_gate=not critical_failures,
        timestamp_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def _scope_score(changed_files: list[str], planned_files: list[str]) -> tuple[int, list[str]]:
    if not changed_files:
        return 20, []
    if not planned_files:
        return 20, []

    unmatched = [path for path in changed_files if not _matches_plan(path, planned_files)]
    if not unmatched:
        return 20, []

    matched_count = len(changed_files) - len(unmatched)
    ratio = matched_count / len(changed_files)
    points = int(round(20 * ratio))
    advisory = f"scope drift: changed outside plan: {', '.join(unmatched[:8])}"
    return points, [advisory]


def _matches_plan(path: str, planned_files: list[str]) -> bool:
    for planned in planned_files:
        normalized = planned.strip()
        if not normalized:
            continue
        if path == normalized:
            return True
        if normalized.endswith("/"):
            if path.startswith(normalized):
                return True
            continue
        if path.startswith(f"{normalized}/"):
            return True
    return False
