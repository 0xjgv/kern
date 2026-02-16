from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .types import IterationEvaluation, StageExecution, StageSpec


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RunLogger:
    def __init__(self, kern_dir: Path, run_id: str) -> None:
        self.run_id = run_id
        self.runs_dir = kern_dir / "runs" / run_id
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.runs_dir / "events.jsonl"
        self.reports_dir = kern_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def log_stage_event(
        self,
        *,
        task_id: int | None,
        stage: StageSpec,
        model: str,
        started_at: str,
        ended_at: str,
        duration_ms: int,
        execution: StageExecution,
    ) -> None:
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "task_id": task_id,
            "stage_number": stage.number,
            "stage_name": stage.name,
            "model": model,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_ms": duration_ms,
            "success": execution.success,
            "skip": execution.skip,
            "queue_empty": execution.queue_empty,
            "usage": execution.usage,
            "total_cost_usd": execution.total_cost_usd,
        }
        if execution.error:
            payload["error"] = execution.error
        self._append_jsonl(self.events_file, payload)

    def append_evaluation(self, evaluation: IterationEvaluation) -> Path:
        report_file = self.reports_dir / f"task-{evaluation.task_id}.jsonl"
        self._append_jsonl(
            report_file,
            {
                "task_id": evaluation.task_id,
                "attempt": evaluation.attempt,
                "score": evaluation.score,
                "critical_failures": evaluation.critical_failures,
                "advisories": evaluation.advisories,
                "passed_soft_gate": evaluation.passed_soft_gate,
                "timestamp_utc": evaluation.timestamp_utc,
            },
        )
        return report_file

    def previous_score(self, task_id: int) -> int | None:
        report_file = self.reports_dir / f"task-{task_id}.jsonl"
        if not report_file.exists():
            return None
        last_score: int | None = None
        for line in report_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            score = payload.get("score")
            if isinstance(score, int):
                last_score = score
        return last_score

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
