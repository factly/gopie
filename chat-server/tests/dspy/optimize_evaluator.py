import json
import sys
from datetime import datetime
from pathlib import Path

import dspy

from tests.dspy.data_loader import GoldenDatasetLoader
from tests.dspy.signatures import EvaluateQueryResponse
from tests.test_config import TestConfig


def evaluation_score_metric(example, prediction, trace=None) -> float:
    try:
        pred_score = max(0, min(10, float(prediction.evaluation_score)))
        true_score = max(0, min(10, float(example.evaluation_score)))
        mae = abs(pred_score - true_score)

        if mae <= 1.0:
            return 1.0
        if mae <= 2.0:
            return 0.8
        if mae <= 3.0:
            return 0.6
        if mae <= 5.0:
            return 0.4
        return 0.2
    except (ValueError, AttributeError):
        return 0.0


class EvaluatorModule(dspy.Module):
    """
    DSPy module for query response evaluation.

    Uses ChainOfThought to provide reasoning-based scoring.
    For simpler/faster evaluation, you can use dspy.Predictor instead.
    """

    def __init__(self, use_reasoning: bool = True) -> None:
        super().__init__()
        if use_reasoning:
            self.evaluate = dspy.ChainOfThought(EvaluateQueryResponse)
        else:
            self.evaluate = dspy.Predictor(EvaluateQueryResponse)

    def forward(self, generated_answer: str, expected_result: str):
        """Evaluate a generated answer against expected result."""
        return self.evaluate(generated_answer=generated_answer, expected_result=expected_result)


def prepare_dspy_examples(examples, *, verbose: bool = False) -> list:
    dspy_examples = []

    for i, ex in enumerate(examples):
        generated_answer_str = json.dumps(ex.generated_answer, indent=2)
        expected_result_str = (
            json.dumps(ex.expected_result)
            if isinstance(ex.expected_result, dict)
            else str(ex.expected_result)
        )

        dspy_ex = dspy.Example(
            generated_answer=generated_answer_str,
            expected_result=expected_result_str,
            evaluation_score=ex.ground_truth_score,
            reasoning=ex.reasoning,
            summary=ex.summary,
        ).with_inputs("generated_answer", "expected_result")

        dspy_examples.append(dspy_ex)

        if verbose and (i + 1) % 10 == 0:
            print(f"  Converted {i + 1}/{len(examples)} examples")

    return dspy_examples


def optimize_evaluator(
    dataset_path: str,
    output_dir: str = "tests/dspy/output",
    train_ratio: float = 0.7,
    max_bootstrapped_demos: int = 8,
    max_labeled_demos: int = 4,
    seed: int = 42,
    use_reasoning: bool = True,
) -> tuple:
    """
    Optimize evaluation prompt using DSPy BootstrapFewShot.

    BootstrapFewShot automatically finds the best few-shot examples
    from your training data to improve evaluation accuracy.
    """
    print("🚀 Starting DSPy Evaluation Optimization\n")

    print(f"📦 Configuring DSPy with model: {TestConfig.DEFAULT_LLM_MODEL}")
    lm = dspy.LM(
        model=f"openai/{TestConfig.DEFAULT_LLM_MODEL}",
        api_key=TestConfig.OPENAI_API_KEY,
        max_tokens=1000,
    )
    dspy.configure(lm=lm)

    print(f"\n📂 Loading dataset from: {dataset_path}")
    loader = GoldenDatasetLoader(dataset_path)
    train_examples, test_examples = loader.split_data(train_ratio=train_ratio, seed=seed)

    print(f"\n📊 Dataset split:")
    print(f"  Training: {len(train_examples)} examples")
    print(f"  Testing: {len(test_examples)} examples")

    stats = loader.get_statistics()
    print(f"\n📈 Score Distribution (User Evaluation):")
    for label, count in stats["score_distribution"].items():
        print(f"  {label}: {count} ({count/stats['total_examples']*100:.1f}%)")
    print(f"\n📊 Score Statistics (User Evaluation):")
    for stat_name, value in stats["score_stats"].items():
        print(f"  {stat_name}: {value:.2f}")

    print(f"\n🔄 Converting to DSPy format...")
    train_set = prepare_dspy_examples(train_examples, verbose=True)
    test_set = prepare_dspy_examples(test_examples, verbose=False)

    print(f"\n🏗️  Creating base evaluator...")
    evaluator = EvaluatorModule(use_reasoning=use_reasoning)

    print(f"\n🎯 Optimizing with BootstrapFewShot...")
    print(f"  Max bootstrapped demos: {max_bootstrapped_demos}")
    print(f"  Max labeled demos: {max_labeled_demos}")

    optimizer = dspy.BootstrapFewShot(
        metric=evaluation_score_metric,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
    )

    print(f"\n⚡ Running optimization (this may take a few minutes)...")
    optimized_evaluator = optimizer.compile(evaluator, trainset=train_set)

    # 6. Evaluate on test set
    print(f"\n🧪 Evaluating on test set...")
    total_mae = 0.0
    total_metric_score = 0.0
    results = []

    for ex in test_set:
        try:
            pred = optimized_evaluator(
                generated_answer=ex.generated_answer, expected_result=ex.expected_result
            )

            # Calculate MAE
            pred_score = float(pred.evaluation_score)
            true_score = float(ex.evaluation_score)
            mae = abs(pred_score - true_score)
            total_mae += mae

            # Calculate metric score
            metric_score = evaluation_score_metric(ex, pred)
            total_metric_score += metric_score

            results.append(mae)
        except Exception as e:
            print(f"  ⚠️  Error evaluating example: {e}")
            results.append(float(ex.evaluation_score))

    avg_mae = total_mae / len(test_set) if test_set else 0.0
    avg_metric_score = total_metric_score / len(test_set) if test_set else 0.0

    # 7. Calculate detailed metrics
    print("\n✅ Optimization complete!")
    print("\n📊 Results:")
    print(f"  Average MAE: {avg_mae:.2f} points")
    print(f"  Average Metric Score: {avg_metric_score * 100:.2f}%")
    print(f"  Test Cases: {len(test_set)}")

    # Score distribution analysis
    score_ranges = {
        "within_1_point": sum(1 for r in results if r <= 1.0),
        "within_2_points": sum(1 for r in results if r <= 2.0),
        "within_3_points": sum(1 for r in results if r <= 3.0),
        "more_than_3_points": sum(1 for r in results if r > 3.0),
    }

    print("\n🎯 Prediction Accuracy:")
    for range_name, count in score_ranges.items():
        pct = (count / len(results) * 100) if results else 0
        label = range_name.replace("_", " ").title()
        print(f"  {label}: {count} ({pct:.1f}%)")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = output_path / f"optimized_evaluator_{timestamp}.json"

    print(f"\n💾 Saving optimized evaluator to: {save_path}")
    optimized_evaluator.save(str(save_path))

    # Save metrics
    metrics = {
        "timestamp": timestamp,
        "model": TestConfig.DEFAULT_LLM_MODEL,
        "dataset_path": str(dataset_path),
        "train_size": len(train_examples),
        "test_size": len(test_examples),
        "avg_mae": avg_mae,
        "avg_metric_score": avg_metric_score,
        "max_bootstrapped_demos": max_bootstrapped_demos,
        "max_labeled_demos": max_labeled_demos,
        "accuracy_breakdown": score_ranges,
    }

    metrics_path = output_path / f"optimization_metrics_{timestamp}.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"💾 Metrics saved to: {metrics_path}")

    return optimized_evaluator, metrics


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Optimize evaluation prompt using DSPy")
    parser.add_argument(
        "--dataset",
        type=str,
        default="tests/chat_server_tests/labeled_golden.json",
        help="Path to labeled golden dataset JSON",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="tests/dspy/output",
        help="Directory to save optimized evaluator",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.7,
        help="Ratio of data for training (default: 0.7)",
    )
    parser.add_argument(
        "--max-bootstrapped",
        type=int,
        default=8,
        help="Max bootstrapped demos (default: 8)",
    )
    parser.add_argument("--max-labeled", type=int, default=4, help="Max labeled demos (default: 4)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--no-reasoning",
        action="store_true",
        help="Use simple Predictor instead of ChainOfThought (faster, no reasoning)",
    )

    args = parser.parse_args()

    if not Path(args.dataset).exists():
        print(f"❌ Error: Dataset not found at {args.dataset}")
        sys.exit(1)

    try:
        optimize_evaluator(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            train_ratio=args.train_ratio,
            max_bootstrapped_demos=args.max_bootstrapped,
            max_labeled_demos=args.max_labeled,
            seed=args.seed,
            use_reasoning=not args.no_reasoning,
        )

        print("\n✨ Success! Optimized evaluator ready for use.")
        print(
            "\n💡 To use the optimized evaluator, load it from the saved path and call evaluate()."
        )

    except Exception as e:
        print(f"\n❌ Error during optimization: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
