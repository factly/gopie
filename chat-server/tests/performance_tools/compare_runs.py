import argparse
import sys

from tests.performance_tools.performance_tracker import PerformanceTracker


def list_runs(tracker: PerformanceTracker, limit: int | None = None):
    runs = tracker.list_runs(limit=limit)

    if not runs:
        print("No test runs found in performance history.")
        return

    print(f"\n{'='*120}")
    print(
        f"{'RUN ID':<30} {'TIMESTAMP':<20} {'EVALUATOR':<10} {'TESTS':<8} {'AVG SCORE':<12} {'AVG TIME':<10}"
    )
    print(f"{'='*120}")

    for run in runs:
        run_id = run["run_id"]
        timestamp = run["timestamp"][:19]
        evaluator = run["model_config"]["evaluator_type"].upper()
        summary = run["summary"]

        total = summary["total_tests"]
        avg_score = summary.get("avg_score", 0)
        avg_time = summary["avg_request_time"]

        print(
            f"{run_id:<30} {timestamp:<20} {evaluator:<10} {total:<8} {avg_score:<11.2f} {avg_time:<9.2f}s"
        )

    print(f"{'='*120}\n")
    print(f"Total runs: {len(runs)}")
    if limit:
        print(f"Showing most recent {limit} runs")


def show_run(tracker: PerformanceTracker, run_id: str):
    run = tracker.get_run(run_id)

    if not run:
        print(f"Run '{run_id}' not found.")
        return

    print(f"\n{'='*70}")
    print(f"RUN DETAILS: {run_id}")
    print(f"{'='*70}")

    print(f"\nTimestamp: {run['timestamp']}")
    print(f"Notes: {run.get('notes', 'N/A')}")

    print(f"\nModel Configuration:")
    config = run["model_config"]
    print(f"  FAST:     {config['fast_model']}")
    print(f"  BALANCED: {config['balanced_model']}")
    print(f"  ADVANCED: {config['advanced_model']}")
    print(f"  EVALUATOR: {config['evaluator_type'].upper()}")

    print(f"\nPerformance Metrics:")
    summary = run["summary"]
    print(f"  Total Time:       {summary['total_time']:.2f}s")
    print(f"  Average per Test: {summary['avg_request_time']:.2f}s")
    print(f"  Median per Test:  {summary['median_request_time']:.2f}s")
    print(f"  Min Time:         {summary['min_request_time']:.2f}s")
    print(f"  Max Time:         {summary['max_request_time']:.2f}s")

    print(f"\nTest Results:")
    print(f"  Total Tests:      {summary['total_tests']}")
    print(f"  Average Score:    {summary.get('avg_score', 0):.2f}/10")
    print(f"  Median Score:     {summary.get('median_score', 0):.2f}/10")
    print(f"  Min Score:        {summary.get('min_score', 0):.2f}/10")
    print(f"  Max Score:        {summary.get('max_score', 0):.2f}/10")

    if summary.get("errors", 0) > 0:
        print(f"  Errors:           {summary['errors']}")

    print(f"\nResults File: {run.get('results_file', 'N/A')}")
    print(f"{'='*70}\n")


def compare_all_runs(tracker: PerformanceTracker, limit: int | None = None):
    runs = tracker.list_runs(limit=limit)

    if not runs:
        print("No test runs found in performance history.")
        return

    if len(runs) == 1:
        print("Only one run found. Use 'show <run_id>' for details.")
        return

    best_avg_score = max(run["summary"].get("avg_score", 0) for run in runs)
    fastest_avg_time = min(run["summary"].get("avg_request_time", float("inf")) for run in runs)

    def mark_best(value: float, best_value: float, higher_is_better: bool = True) -> str:
        if best_value in (float("inf"), float("-inf")):
            return ""
        if higher_is_better and value == best_value:
            return "*"
        if not higher_is_better and value == best_value:
            return "*"
        return ""

    print(f"\n{'='*200}")
    print("RUN COMPARISON (all recorded runs)")
    print(f"{'='*200}\n")

    header = (
        f"{'RUN ID':<26} {'TIMESTAMP':<20} "
        f"{'FAST MODEL':<20} {'BALANCED MODEL':<20} {'ADVANCED MODEL':<20} "
        f"{'AVG SCORE':<12} {'MEDIAN SCORE':<13} {'AVG TIME (s)':<14} "
        f"{'MEDIAN TIME (s)':<16} {'TESTS':<8}"
    )
    print(header)
    print("-" * min(len(header), 200))

    for run in runs:
        summary = run["summary"]
        config = run["model_config"]

        fast = config.get("fast_model", "n/a")[:20]
        balanced = config.get("balanced_model", "n/a")[:20]
        advanced = config.get("advanced_model", "n/a")[:20]

        avg_score = summary.get("avg_score", 0.0)
        median_score = summary.get("median_score", 0.0)
        avg_time = summary.get("avg_request_time", 0.0)
        median_time = summary.get("median_request_time", 0.0)
        total_tests = summary.get("total_tests", 0)

        avg_score_str = f"{avg_score:>6.2f}{mark_best(avg_score, best_avg_score)}"
        median_score_str = f"{median_score:>6.2f}"
        avg_time_str = (
            f"{avg_time:>8.2f}{mark_best(avg_time, fastest_avg_time, higher_is_better=False)}"
        )
        median_time_str = f"{median_time:>8.2f}"

        print(
            f"{run['run_id']:<26} {run['timestamp'][:19]:<20} "
            f"{fast:<20} {balanced:<20} {advanced:<20} "
            f"{avg_score_str:<12} {median_score_str:<13} "
            f"{avg_time_str:<14} {median_time_str:<16} {total_tests:<8}"
        )

    print("\n* denotes the best value for that metric")
    if limit:
        print(f"Showing most recent {limit} runs.")


def find_best(tracker: PerformanceTracker, metric: str = "avg_score"):
    best_run = tracker.get_best_run(metric=metric)

    if not best_run:
        print("No runs found.")
        return

    print(f"\nBest run by {metric}:")
    show_run(tracker, best_run["run_id"])


def main():
    parser = argparse.ArgumentParser(
        description="Compare model performance across test runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  list              - Show all test runs
  show <run_id>     - Show detailed results for a specific run
  compare           - Compare all recorded runs side-by-side
  best [metric]     - Show best performing run (default: avg_score)

Examples:
  python -m tests.performance_tools.compare_runs list
  python -m tests.performance_tools.compare_runs show 20250112_143022_gpt4o
  python -m tests.performance_tools.compare_runs compare --limit 5
  python -m tests.performance_tools.compare_runs best avg_score
        """,
    )

    parser.add_argument(
        "command", choices=["list", "show", "compare", "best"], help="Command to execute"
    )
    parser.add_argument("args", nargs="*", help="Additional arguments for the command")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of runs to show (for 'list' or 'compare' commands)",
    )

    args = parser.parse_args()
    tracker = PerformanceTracker()

    try:
        if args.command == "list":
            list_runs(tracker, limit=args.limit)

        elif args.command == "show":
            if len(args.args) < 1:
                print("Error: 'show' command requires run_id")
                sys.exit(1)
            show_run(tracker, args.args[0])

        elif args.command == "compare":
            if args.args:
                print("Warning: 'compare' command now compares all runs and ignores run IDs.")
            compare_all_runs(tracker, limit=args.limit)

        elif args.command == "best":
            metric = args.args[0] if args.args else "avg_score"
            find_best(tracker, metric=metric)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
