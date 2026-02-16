from __future__ import annotations

from pathlib import Path

from claude_code_sdk import AssistantMessage, ClaudeCodeOptions, ResultMessage, query

from .stage_output import parse_stage_output
from .types import StageExecution, StageRunner, StageSpec


class ClaudeSdkRunner(StageRunner):
    def __init__(self, env: dict[str, str], verbose: bool = False) -> None:
        self._env = env
        self._verbose = verbose

    async def run_stage(self, stage: StageSpec, prompt: str, cwd: Path, model: str) -> StageExecution:
        kwargs: dict[str, object] = {
            "model": model,
            "cwd": str(cwd),
            "env": self._env,
        }
        if stage.allowed_tools is not None:
            kwargs["allowed_tools"] = stage.allowed_tools
        if stage.permission_mode != "default":
            kwargs["permission_mode"] = stage.permission_mode
        options = ClaudeCodeOptions(**kwargs)

        result_text: str | None = None
        assistant_texts: list[str] = []
        result_usage: dict[str, object] | None = None
        total_cost_usd: float | None = None
        result_error: bool = False
        result_subtype: str | None = None
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage) and message.result:
                result_text = message.result
                result_usage = message.usage
                total_cost_usd = message.total_cost_usd
                result_error = message.is_error
                result_subtype = message.subtype
                continue
            if isinstance(message, ResultMessage):
                result_usage = message.usage
                total_cost_usd = message.total_cost_usd
                result_error = message.is_error
                result_subtype = message.subtype
                continue
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    text = getattr(block, "text", None)
                    if text:
                        assistant_texts.append(text)

        raw_output = (result_text or "\n".join(assistant_texts)).strip()
        if not raw_output:
            raw_output = "FAILED: empty stage output"
        parsed = parse_stage_output(raw_output, stage.number)
        if result_error and parsed.success:
            parsed.success = False
            parsed.error = f"SDK returned error subtype={result_subtype or 'unknown'}"
        parsed.usage = result_usage
        parsed.total_cost_usd = total_cost_usd
        return parsed
