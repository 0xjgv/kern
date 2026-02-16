from pathlib import Path

from kern.handoff import append_handoff_block, ensure_handoff_dir, handoff_path, init_handoff_file


def test_init_and_append_handoff(tmp_path: Path) -> None:
    handoff_dir = tmp_path / ".kern" / "handoff"
    ensure_handoff_dir(handoff_dir)
    file_path = handoff_path(handoff_dir, 9)
    init_handoff_file(file_path, task_id=9, hint="", run_dir=tmp_path)
    append_handoff_block(file_path, "## Research\n- Summary: x", required=True)
    content = file_path.read_text(encoding="utf-8")
    assert "Task ID: 9" in content
    assert "## Research" in content


def test_append_handoff_requires_block(tmp_path: Path) -> None:
    file_path = tmp_path / "handoff.md"
    file_path.write_text("# Task Handoff\n", encoding="utf-8")
    try:
        append_handoff_block(file_path, None, required=True)
    except RuntimeError:
        return
    raise AssertionError("append_handoff_block should fail when required block is missing")
