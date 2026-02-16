from kern.stage_output import extract_handoff_block, parse_stage_output


def test_parse_stage_output_stage1_with_task_and_skip() -> None:
    output = """
<<MACHINE>>
{"stage":1,"status":"success","task_id":12,"queue_empty":false,"skip":true,"summary":"done","metadata":{}}
<<END_MACHINE>>
<<HANDOFF>>
## Research
- Summary: done
<<END_HANDOFF>>
SUCCESS task_id=12 skip=true
""".strip()
    parsed = parse_stage_output(output, 1)
    assert parsed.success is True
    assert parsed.task_id == 12
    assert parsed.skip is True
    assert parsed.queue_empty is False
    assert parsed.handoff_block == "## Research\n- Summary: done"


def test_parse_stage_output_machine_coerces_string_values() -> None:
    output = """
<<MACHINE>>
{"stage":"1","status":"SUCCESS","task_id":"12","queue_empty":"false","skip":"false","summary":"done","metadata":{}}
<<END_MACHINE>>
<<HANDOFF>>
## Research
- Summary: done
<<END_HANDOFF>>
SUCCESS task_id=12
""".strip()
    parsed = parse_stage_output(output, 1)
    assert parsed.success is True
    assert parsed.task_id == 12


def test_parse_stage_output_stage1_queue_empty() -> None:
    output = """
<<MACHINE>>
{"stage":1,"status":"success","task_id":null,"queue_empty":true,"skip":false,"summary":"empty","metadata":{}}
<<END_MACHINE>>
<<HANDOFF>>
## Research
- Summary: none
<<END_HANDOFF>>
SUCCESS task_id=none
""".strip()
    parsed = parse_stage_output(output, 1)
    assert parsed.success is True
    assert parsed.task_id is None
    assert parsed.queue_empty is True


def test_parse_stage_output_missing_machine_fails() -> None:
    output = """
<<HANDOFF>>
## Design
- Decisions: x
<<END_HANDOFF>>
SUCCESS task_id=7
""".strip()
    parsed = parse_stage_output(output, 2)
    assert parsed.success is False
    assert "Missing <<MACHINE>> block" in (parsed.error or "")


def test_parse_stage_output_invalid_success_line_fails() -> None:
    output = """
<<MACHINE>>
{"stage":6,"status":"success","task_id":7,"queue_empty":false,"skip":false,"summary":"done"}
<<END_MACHINE>>
SUCCESS task_id=7
""".strip()
    parsed = parse_stage_output(output, 6)
    assert parsed.success is False
    assert "Invalid SUCCESS line" in (parsed.error or "")


def test_parse_stage6_allows_machine_queue_flags() -> None:
    output = """
<<MACHINE>>
{"stage":6,"status":"success","task_id":7,"queue_empty":true,"skip":true,"summary":"done"}
<<END_MACHINE>>
SUCCESS
""".strip()
    parsed = parse_stage_output(output, 6)
    assert parsed.success is True
    assert parsed.task_id == 7


def test_parse_stage0_allows_success_line_before_trailing_text() -> None:
    output = """
SUCCESS created=1 existing=0
```
""".strip()
    parsed = parse_stage_output(output, 0)
    assert parsed.success is True


def test_parse_stage0_allows_missing_success_line_when_no_failure_token() -> None:
    parsed = parse_stage_output("Queue synchronized.", 0)
    assert parsed.success is True


def test_extract_handoff_block_missing_markers() -> None:
    assert extract_handoff_block("SUCCESS") is None
