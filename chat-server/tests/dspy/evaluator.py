import json
from pathlib import Path

import dspy

from tests.dspy.optimize_evaluator import EvaluatorModule
from tests.test_config import TestConfig


class OptimizedEvaluator:
    def __init__(self, evaluator_path: Path | None = None) -> None:
        lm = dspy.LM(
            model=TestConfig.DEFAULT_LLM_MODEL,
            api_key=TestConfig.OPENAI_API_KEY,
            max_tokens=1000,
        )
        dspy.configure(lm=lm)

        if evaluator_path is None:
            evaluator_path = self._find_latest_evaluator()

        if evaluator_path is None:
            msg = (
                "No optimized DSPy evaluator found. "
                "Run `python -m tests.dspy.optimize_evaluator` to generate one."
            )
            raise FileNotFoundError(msg)

        print(f"Loading DSPy evaluator from: {evaluator_path}")
        self.evaluator = EvaluatorModule()

        try:
            self.evaluator.load(str(evaluator_path))
            self.evaluator_path = evaluator_path
        except Exception as e:
            msg = (
                f"Failed to load DSPy evaluator from {evaluator_path}\n"
                f"Error: {e}\n\n"
                "The evaluator file may be corrupted. Try re-running optimization:\n"
                "  python -m tests.dspy.optimize_evaluator"
            )
            raise RuntimeError(msg) from e

    def _find_latest_evaluator(self) -> Path | None:
        output_dir = Path(__file__).parent / "output"
        if not output_dir.exists():
            return None

        evaluator_files = list(output_dir.glob("optimized_evaluator_*.json"))
        if not evaluator_files:
            return None

        return max(evaluator_files, key=lambda p: p.stat().st_mtime)

    def evaluate(
        self,
        generated_answer: dict | str,
        expected_result: str | dict,
    ) -> dict:
        generated_answer_str = (
            json.dumps(generated_answer, indent=2)
            if isinstance(generated_answer, dict)
            else str(generated_answer)
        )

        expected_result_str = (
            json.dumps(expected_result)
            if isinstance(expected_result, dict)
            else str(expected_result)
        )

        try:
            result = self.evaluator(
                generated_answer=generated_answer_str,
                expected_result=expected_result_str,
            )
            return {
                "evaluation_score": float(result.evaluation_score),
                "reasoning": result.reasoning,
                "summary": result.summary,
            }
        except Exception as e:
            print("[DSPy Warning] Structured output failed, falling back to JSON mode.")
            print(f"Raw generated_answer: {generated_answer_str}")
            print(f"Raw expected_result: {expected_result_str}")
            print(f"Error: {e}")
            print("Tip: Use GPT-4o or GPT-4 for best structured output reliability.")
            return {
                "evaluation_score": 0.0,
                "reasoning": f"Structured output failed: {e}",
                "summary": "Evaluator fallback to JSON mode. Check model compatibility.",
            }
