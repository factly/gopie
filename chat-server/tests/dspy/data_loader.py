import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvaluationExample:
    query: str
    query_type: str
    data_type: str
    generated_answer: dict
    expected_result: str
    ground_truth_score: float
    user_evaluation: float
    reasoning: str
    summary: str
    feedback_type: str
    user_feedback: str


class GoldenDatasetLoader:
    def __init__(self, dataset_path: str | Path) -> None:
        self.dataset_path = Path(dataset_path)
        self.examples: list[EvaluationExample] = []

    def load(self) -> list[EvaluationExample]:
        with open(self.dataset_path) as f:
            data = json.load(f)

        self.examples = []
        for item in data:
            if "User Evaluation" not in item:
                continue

            selected_datasets = item.get("Selected Datasets", "")
            datasets_list = selected_datasets.split("; ") if selected_datasets else []

            tool_messages = item.get("Tool Messages", "")
            processing_steps = tool_messages.split(" | ") if tool_messages else []

            generated_answer = {
                "ai_response": item.get("Response", ""),
                "datasets_used": datasets_list,
                "processing_steps": processing_steps,
                "visualization_results": [],
                "metadata": {
                    "dataset_count": len(datasets_list),
                    "sql_query_count": item.get("SQL Query Count", 0),
                    "processing_step_count": len(processing_steps),
                    "visualization_count": item.get("Visualization Count", 0),
                },
            }

            user_score = float(item.get("User Evaluation", 0))

            example = EvaluationExample(
                query=item.get("Query", ""),
                query_type=item.get("Query Type", "data"),
                data_type=item.get("Data Type", "single"),
                generated_answer=generated_answer,
                expected_result=f"Dataset: {item.get('Dataset Name', '')}",
                ground_truth_score=user_score,
                user_evaluation=user_score,
                reasoning=item.get("AI Reasoning", ""),
                summary=item.get("AI Summary", ""),
                feedback_type=item.get("Feedback Type", ""),
                user_feedback=item.get("User Feedback", ""),
            )
            self.examples.append(example)

        return self.examples

    def split_data(
        self, train_ratio: float = 0.7, seed: int = 42
    ) -> tuple[list[EvaluationExample], list[EvaluationExample]]:
        if not self.examples:
            self.load()

        random.seed(seed)
        shuffled = self.examples.copy()
        random.shuffle(shuffled)

        split_idx = int(len(shuffled) * train_ratio)
        return shuffled[:split_idx], shuffled[split_idx:]

    def get_statistics(self) -> dict:
        if not self.examples:
            self.load()

        user_scores = [e.ground_truth_score for e in self.examples]

        return {
            "total_examples": len(self.examples),
            "score_distribution": {
                "score_0": sum(1 for e in self.examples if e.ground_truth_score == 0),
                "score_5": sum(1 for e in self.examples if e.ground_truth_score == 5),
                "score_10": sum(1 for e in self.examples if e.ground_truth_score == 10),
                "score_0-4": sum(1 for e in self.examples if 0 <= e.ground_truth_score < 5),
                "score_5-7": sum(1 for e in self.examples if 5 <= e.ground_truth_score < 8),
                "score_8-10": sum(1 for e in self.examples if 8 <= e.ground_truth_score <= 10),
            },
            "score_stats": {
                "user_avg": sum(user_scores) / len(user_scores) if user_scores else 0,
                "user_min": min(user_scores) if user_scores else 0,
                "user_max": max(user_scores) if user_scores else 0,
            },
            "by_query_type": {
                "data": sum(1 for e in self.examples if e.query_type == "data"),
                "viz": sum(1 for e in self.examples if e.query_type == "viz"),
            },
            "by_data_type": {
                "single": sum(1 for e in self.examples if e.data_type == "single"),
                "multi": sum(1 for e in self.examples if e.data_type == "multi"),
            },
        }
