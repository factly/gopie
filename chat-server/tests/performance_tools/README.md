# Performance Tools

Track and compare test runs across different model configurations.

## Files

| File                        | Purpose                      |
| --------------------------- | ---------------------------- |
| `performance_tracker.py`    | Save/load run history        |
| `compare_runs.py`           | CLI for comparing runs       |
| `generate_summary_image.py` | Generate static PNG for docs |

## CLI Usage

```bash
# List all runs
python -m tests.performance_tools.compare_runs list

# Show specific run details
python -m tests.performance_tools.compare_runs show <run_id>

# Compare all runs side-by-side
python -m tests.performance_tools.compare_runs compare
python -m tests.performance_tools.compare_runs compare --limit 10

# Find best performing run
python -m tests.performance_tools.compare_runs best avg_score
python -m tests.performance_tools.compare_runs best avg_request_time
```

## Generate Summary Image for Docs

Generate a clean PNG image for documentation (outputs to `docs/images/performance_summary.png`):

```bash
python -m tests.performance_tools.generate_summary_image
```

## Metrics Reference

| Metric                    | Description                         |
| ------------------------- | ----------------------------------- |
| `avg_score`               | Average evaluation score (0-10)     |
| `median_score`            | Median evaluation score             |
| `min_score` / `max_score` | Score range                         |
| `avg_request_time`        | Average API response time (seconds) |
| `median_request_time`     | Median response time                |
| `total_time`              | Total run duration                  |
| `total_tests`             | Number of test cases                |
| `errors`                  | Failed test count                   |

## Performance History Format

Stored in `tests/chat_server_tests/output/performance_history.json`:

```json
{
  "runs": [
    {
      "run_id": "20250112_143022_gpt4o",
      "timestamp": "2025-01-12T14:30:22",
      "model_config": {
        "fast_model": "gpt-4o-mini",
        "balanced_model": "gpt-4o-mini",
        "advanced_model": "gpt-4o",
        "evaluator_type": "dspy"
      },
      "summary": {
        "avg_score": 7.85,
        "avg_request_time": 3.45,
        "total_tests": 25
      }
    }
  ]
}
```
