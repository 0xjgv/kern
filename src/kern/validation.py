from __future__ import annotations

from pathlib import Path
import re
import subprocess

from .types import SuccessCriterion, ValidationCheckResult, ValidationResult, Validator

CRITERION_RE = re.compile(
    r"^\s*(file_exists|file_contains|file_not_contains|command_succeeds|git_diff_includes)\s*:\s*(.+)\s*$"
)


def _strip_ticks(value: str) -> str:
    return value.strip().strip("`").strip()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SuccessCriteriaValidator(Validator):
    def validate(
        self,
        task_id: int,
        run_dir: Path,
        handoff_file: Path,
        criteria: list[SuccessCriterion] | None = None,
    ) -> ValidationResult:
        if not handoff_file.exists():
            return ValidationResult(
                passed=False,
                checks=[
                    ValidationCheckResult(
                        "handoff_file_exists",
                        "handoff_file_exists",
                        False,
                        f"{handoff_file} not found",
                    )
                ],
            )

        active_criteria = criteria if criteria is not None else self._extract_criteria_from_handoff(handoff_file)
        if not active_criteria:
            return ValidationResult(
                passed=True,
                checks=[
                    ValidationCheckResult(
                        "success_criteria_present",
                        "success_criteria_present",
                        True,
                        "No explicit criteria found; skipping gate",
                    )
                ],
            )

        checks: list[ValidationCheckResult] = []
        diff_names = self._diff_names(run_dir)
        diff_patch = self._diff_patch(run_dir)
        for criterion in active_criteria:
            kind = criterion.kind
            payload = criterion.value
            label = f"{kind}: {payload}"

            if kind == "file_exists":
                path = run_dir / _strip_ticks(payload)
                checks.append(ValidationCheckResult(label, kind, path.exists(), f"path={path}"))
                continue

            if kind in {"file_contains", "file_not_contains"}:
                file_part, pattern_part = self._split_file_pattern(payload)
                file_path = run_dir / _strip_ticks(file_part)
                if not file_path.exists():
                    checks.append(ValidationCheckResult(label, kind, False, f"path not found: {file_path}"))
                    continue
                content = _read_text(file_path)
                pattern = _strip_ticks(pattern_part)
                matched, mode = self._match_pattern(content, pattern)
                passed = matched if kind == "file_contains" else not matched
                checks.append(
                    ValidationCheckResult(
                        label,
                        kind,
                        passed,
                        f"path={file_path} pattern={pattern} mode={mode}",
                    )
                )
                continue

            if kind == "command_succeeds":
                command = _strip_ticks(payload)
                completed = subprocess.run(
                    command,
                    cwd=run_dir,
                    shell=True,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                details = f"exit={completed.returncode}"
                if completed.stderr.strip():
                    details = f"{details} stderr={completed.stderr.strip()[:200]}"
                checks.append(ValidationCheckResult(label, kind, completed.returncode == 0, details))
                continue

            if kind == "git_diff_includes":
                needle = _strip_ticks(payload)
                by_name = any(needle in name for name in diff_names)
                by_patch = bool(needle) and (needle in diff_patch)
                passed = by_name or by_patch
                checks.append(
                    ValidationCheckResult(
                        label,
                        kind,
                        passed,
                        f"matched={passed} by_name={by_name} by_patch={by_patch} files={','.join(diff_names) or 'none'}",
                    )
                )
                continue

        passed = all(check.passed for check in checks)
        return ValidationResult(passed=passed, checks=checks)

    def _extract_criteria_from_handoff(self, handoff_file: Path) -> list[SuccessCriterion]:
        criteria: list[SuccessCriterion] = []
        in_plan = False
        in_success_criteria = False
        for raw_line in _read_text(handoff_file).splitlines():
            line = raw_line.strip()
            if line.startswith("## "):
                in_plan = line == "## Plan"
                in_success_criteria = False
                continue
            if not in_plan:
                continue
            if line.lower().startswith("- success criteria:"):
                in_success_criteria = True
                continue
            if not in_success_criteria:
                continue
            if line.startswith("- Next:"):
                in_success_criteria = False
                continue
            if not line.startswith("- "):
                continue
            item = line[2:].strip()
            match = CRITERION_RE.match(item)
            if not match:
                continue
            criteria.append(SuccessCriterion(kind=match.group(1), value=match.group(2)))

        seen: set[tuple[str, str]] = set()
        deduped: list[SuccessCriterion] = []
        for criterion in criteria:
            key = (criterion.kind, criterion.value)
            if key not in seen:
                seen.add(key)
                deduped.append(criterion)
        return deduped

    @staticmethod
    def _split_file_pattern(payload: str) -> tuple[str, str]:
        if "::" not in payload:
            if ":" in payload:
                file_part, pattern_part = payload.split(":", 1)
                return file_part.strip(), pattern_part.strip()
            return payload, ""
        file_part, pattern_part = payload.split("::", 1)
        return file_part.strip(), pattern_part.strip()

    @staticmethod
    def _match_pattern(content: str, pattern: str) -> tuple[bool, str]:
        if pattern.startswith("/") and pattern.endswith("/") and len(pattern) >= 2:
            regex = pattern[1:-1]
            return re.search(regex, content, flags=re.MULTILINE) is not None, "regex"
        return pattern in content, "literal"

    @staticmethod
    def _diff_names(run_dir: Path) -> list[str]:
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

        seen: set[str] = set()
        ordered: list[str] = []
        for name in names:
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return ordered

    @staticmethod
    def _diff_patch(run_dir: Path) -> str:
        chunks: list[str] = []
        for command in (["git", "diff"], ["git", "diff", "--cached"]):
            completed = subprocess.run(
                command,
                cwd=run_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode == 0 and completed.stdout:
                chunks.append(completed.stdout)
        return "\n".join(chunks)
