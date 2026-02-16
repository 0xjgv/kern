from pathlib import Path

from kern.prompting import parse_prompt_template


def test_stage_prompt_body_line_limits() -> None:
    repo = Path(__file__).resolve().parents[1]
    prompts_dir = repo / "prompts"
    for stage in range(1, 7):
        prompt_path = prompts_dir / f"{stage}_{_name(stage)}.md"
        template = parse_prompt_template(prompt_path)
        line_count = len(template.body.strip("\n").splitlines())
        assert line_count <= 33, f"{prompt_path.name} has {line_count} lines"


def test_stage_prompt_contract_markers() -> None:
    repo = Path(__file__).resolve().parents[1]
    prompts_dir = repo / "prompts"
    for stage in range(1, 7):
        body = parse_prompt_template(prompts_dir / f"{stage}_{_name(stage)}.md").body
        assert "<<MACHINE>>" in body
        assert "<<END_MACHINE>>" in body
        assert "SUCCESS" in body
        if stage <= 5:
            assert "<<HANDOFF>>" in body
            assert "<<END_HANDOFF>>" in body


def _name(stage: int) -> str:
    names = {
        1: "research",
        2: "design",
        3: "structure",
        4: "plan",
        5: "implement",
        6: "review_commit",
    }
    return names[stage]
