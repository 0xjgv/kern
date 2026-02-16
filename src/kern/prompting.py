from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

HINT_RE = re.compile(
    r"ignore.*(previous|all).*instructions|disregard.*above|</(system|user|data)>",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PromptTemplate:
    model: str | None
    body: str


def validate_hint(hint: str) -> None:
    if len(hint) > 500:
        raise ValueError("HINT too long (max 500 chars)")
    if HINT_RE.search(hint):
        raise ValueError("HINT contains suspicious pattern")


def wrap_untrusted(source: str, content: str) -> str:
    escaped = re.sub(r"</data>", "<\\/data>", content, flags=re.IGNORECASE)
    return f'<data source="{source}">\n{escaped}\n</data>'


def _run_capture(cwd: Path, command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return "none"
    return completed.stdout.strip() or "none"


def collect_recent_commits(cwd: Path) -> str:
    output = _run_capture(cwd, ["git", "log", "-5", "--format=[%h] %s"])
    lines = output.splitlines()[:80]
    return wrap_untrusted("git-log", "\n".join(lines))


def collect_diff_stat(cwd: Path) -> str:
    output = _run_capture(cwd, ["git", "diff", "--stat"])
    lines = output.splitlines()[:30]
    return wrap_untrusted("git-diff", "\n".join(lines))


def parse_prompt_template(path: Path) -> PromptTemplate:
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("---\n"):
        end = raw.find("\n---\n", 4)
        if end != -1:
            front_matter = raw[4:end]
            body = raw[end + 5 :]
            model = None
            for line in front_matter.splitlines():
                if line.strip().startswith("model:"):
                    model = line.split(":", 1)[1].strip() or None
                    break
            return PromptTemplate(model=model, body=body)
    return PromptTemplate(model=None, body=raw)


def render_prompt(body: str, substitutions: dict[str, str]) -> str:
    rendered = body
    for key, value in substitutions.items():
        rendered = rendered.replace(f"{{{key}}}", value)
    return rendered
