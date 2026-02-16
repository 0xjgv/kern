from __future__ import annotations

import kern.cli as cli


def test_version_flag(capsys) -> None:
    code = cli.main(["--version"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.startswith("kern ")


def test_cli_delegates_to_runtime(monkeypatch) -> None:
    seen = {}

    def fake_run(task_id, max_tasks, hint, dry_run, verbose):
        seen.update(
            {
                "task_id": task_id,
                "max_tasks": max_tasks,
                "hint": hint,
                "dry_run": dry_run,
                "verbose": verbose,
            }
        )
        return 0

    monkeypatch.setattr(cli, "run", fake_run)
    code = cli.main(["-c", "3", "--hint", "x", "-n", "-v", "7"])
    assert code == 0
    assert seen == {
        "task_id": 7,
        "max_tasks": 3,
        "hint": "x",
        "dry_run": True,
        "verbose": True,
    }


def test_count_must_be_positive(capsys) -> None:
    code = cli.main(["-c", "0"])
    captured = capsys.readouterr()
    assert code == 1
    assert "--count must be >= 1" in captured.err
