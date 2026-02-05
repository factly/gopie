import json
from datetime import datetime
from pathlib import Path
from typing import Any


class PerformanceTracker:
    def __init__(self, history_file: str | None = None):
        if history_file is None:
            output_dir = Path(__file__).parent.parent / "chat_server_tests" / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            history_file = str(output_dir / "performance_history.json")

        self.history_file = Path(history_file)
        self._ensure_history_file()

    def _ensure_history_file(self):
        if not self.history_file.exists():
            self.history_file.write_text(json.dumps({"runs": []}, indent=2))

    def generate_run_id(self, model_config: dict[str, str]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_hint = model_config.get(
            "advanced_model", model_config.get("default_model", "unknown")
        )
        model_hint = model_hint.replace("-", "").replace(".", "")[:10]
        return f"{timestamp}_{model_hint}"

    def load_history(self) -> dict[str, Any]:
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"runs": []}

    def save_history(self, history: dict[str, Any]):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def save_run(
        self,
        model_config: dict[str, str],
        summary: dict[str, Any],
        notes: str = "",
        test_cases: list[dict[str, Any]] | None = None,
        results_file: str = "",
    ) -> str:
        history = self.load_history()
        run_id = self.generate_run_id(model_config)
        timestamp = datetime.now().isoformat()

        timing_stats = summary.get("timing", {})
        score_stats = summary.get("score_stats", {})
        scores = summary.get("scores", [])
        total = summary.get("total", 0)
        errors = summary.get("errors", 0)

        run_data = {
            "run_id": run_id,
            "timestamp": timestamp,
            "model_config": model_config,
            "notes": notes,
            "summary": {
                "total_tests": total,
                "scores": scores,
                "avg_score": round(score_stats.get("average", 0), 2),
                "median_score": round(score_stats.get("median", 0), 2),
                "min_score": round(score_stats.get("min", 0), 2),
                "max_score": round(score_stats.get("max", 0), 2),
                "errors": errors,
                "avg_request_time": round(timing_stats.get("avg_request_time", 0), 2),
                "median_request_time": round(timing_stats.get("median_request_time", 0), 2),
                "min_request_time": round(timing_stats.get("min_request_time", 0), 2),
                "max_request_time": round(timing_stats.get("max_request_time", 0), 2),
                "total_time": round(timing_stats.get("total_time", 0), 2),
            },
            "results_file": results_file,
        }

        history["runs"].append(run_data)
        self.save_history(history)
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        history = self.load_history()
        for run in history["runs"]:
            if run["run_id"] == run_id:
                return run
        return None

    def list_runs(self, limit: int | None = None) -> list[dict[str, Any]]:
        history = self.load_history()
        runs = sorted(history["runs"], key=lambda r: r["timestamp"], reverse=True)
        return runs[:limit] if limit else runs

    def get_best_run(self, metric: str = "avg_score") -> dict[str, Any] | None:
        runs = self.load_history()["runs"]
        if not runs:
            return None

        reverse = metric in ["pass_rate", "avg_score", "median_score"]
        return max(
            runs,
            key=lambda r: r["summary"].get(metric, 0 if reverse else float("inf")),
            default=None,
        )
