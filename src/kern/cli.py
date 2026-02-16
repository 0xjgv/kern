from __future__ import annotations

import argparse
import subprocess
import sys

from .runtime import run
from .version import VERSION

UPDATE_URL = "https://raw.githubusercontent.com/0xjgv/kern/main/install.sh"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kern",
        description="Autonomous staged development pipeline.",
    )
    parser.add_argument("task_id", nargs="?", type=int, help="Run a specific task by ID")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Dry-run mode")
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=5,
        help="Max number of tasks to process in queue mode (default: 5)",
    )
    parser.add_argument("--hint", default="", help="Guidance hint for stage prompts")
    parser.add_argument("-V", "--version", action="store_true", help="Print version and exit")
    parser.add_argument("--update", action="store_true", help="Install latest release")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"kern {VERSION}")
        return 0

    if args.update:
        completed = subprocess.run(
            ["bash", "-lc", f"curl -fsSL {UPDATE_URL} | bash"],
            check=False,
        )
        return completed.returncode

    if args.count is not None and args.count < 1:
        print("ERROR: --count must be >= 1", file=sys.stderr)
        return 1

    return run(
        task_id=args.task_id,
        max_tasks=args.count,
        hint=args.hint,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    raise SystemExit(main())
