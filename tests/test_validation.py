from pathlib import Path

from kern.types import SuccessCriterion
from kern.validation import SuccessCriteriaValidator


def test_extract_criteria_reads_only_plan_section(tmp_path: Path) -> None:
    handoff = tmp_path / "task-1.md"
    handoff.write_text(
        "\n".join(
            [
                "# Task Handoff",
                "## Plan",
                "- Success criteria:",
                "- file_contains: README.md: ## Validation Note",
                "- git_diff_includes: ## Validation Note",
                "- Next: Implement",
                "## Validation",
                "- FAIL: file_contains: README.md: ## Validation Note :: path not found",
            ]
        ),
        encoding="utf-8",
    )
    validator = SuccessCriteriaValidator()
    criteria = validator._extract_criteria_from_handoff(handoff)  # noqa: SLF001
    assert criteria == [
        SuccessCriterion(kind="file_contains", value="README.md: ## Validation Note"),
        SuccessCriterion(kind="git_diff_includes", value="## Validation Note"),
    ]


def test_split_file_pattern_supports_single_colon() -> None:
    file_part, pattern = SuccessCriteriaValidator._split_file_pattern("README.md: auto-pass")  # noqa: SLF001
    assert file_part == "README.md"
    assert pattern == "auto-pass"


def test_match_pattern_defaults_to_literal_for_brackets() -> None:
    matched, mode = SuccessCriteriaValidator._match_pattern("- [x] done", "- [x] done")  # noqa: SLF001
    assert matched is True
    assert mode == "literal"


def test_match_pattern_supports_regex_wrapper() -> None:
    matched, mode = SuccessCriteriaValidator._match_pattern("abc123", "/abc\\d+/")  # noqa: SLF001
    assert matched is True
    assert mode == "regex"
