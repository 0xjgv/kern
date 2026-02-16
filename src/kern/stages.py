from __future__ import annotations

from pathlib import Path

from .types import StageSpec


STAGE_DEFINITIONS: tuple[tuple[int, str, str, str, list[str] | None, str], ...] = (
    (
        0,
        "Populate Task Queue",
        "0_populate_queue.md",
        "haiku",
        ["Read", "Glob", "Grep", "LS", "TaskGet", "TaskList", "TaskCreate", "TaskUpdate"],
        "default",
    ),
    (
        1,
        "Research",
        "1_research.md",
        "opus",
        ["Read", "Glob", "Grep", "LS", "TaskGet", "TaskList", "TaskUpdate", "Task"],
        "default",
    ),
    (
        2,
        "Design",
        "2_design.md",
        "opus",
        ["Read", "Glob", "Grep", "LS", "TaskGet", "TaskList", "TaskUpdate", "Task"],
        "default",
    ),
    (
        3,
        "Structure",
        "3_structure.md",
        "opus",
        ["Read", "Glob", "Grep", "LS", "TaskGet", "TaskList", "TaskUpdate", "Task"],
        "default",
    ),
    (
        4,
        "Plan",
        "4_plan.md",
        "opus",
        ["Read", "Glob", "Grep", "LS", "TaskGet", "TaskList", "TaskUpdate", "Task"],
        "default",
    ),
    (
        5,
        "Implement",
        "5_implement.md",
        "opus",
        None,
        "bypassPermissions",
    ),
    (
        6,
        "Review & Commit",
        "6_review_commit.md",
        "haiku",
        ["Read", "Glob", "Grep", "LS", "TaskGet", "TaskList", "TaskUpdate", "Bash"],
        "default",
    ),
)


def stage_specs(prompts_dir: Path) -> dict[int, StageSpec]:
    specs: dict[int, StageSpec] = {}
    for number, name, file_name, default_model, allowed_tools, permission_mode in STAGE_DEFINITIONS:
        prompt_path = prompts_dir / file_name
        specs[number] = StageSpec(
            number=number,
            name=name,
            prompt_path=prompt_path,
            default_model=default_model,
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
        )
    return specs
