from __future__ import annotations

from datetime import datetime
import sys


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(message: str) -> None:
    print(f"[{_ts()}] {message}", file=sys.stderr)


def debug(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[{_ts()}] [DEBUG] {message}", file=sys.stderr)


def die(code: int, message: str) -> int:
    log(f"ERROR: {message}")
    return code
