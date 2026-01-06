# Golden Dataset Evaluation

LLM-based test case generation and evaluation framework for assessing chat server response quality.

## Overview

This module provides tools to:

1. **Generate** test cases from existing project datasets
2. **Run** automated evaluations against the chat server
3. **Label** results manually for training data
4. **Optimize** the evaluator using DSPy

## Prerequisites

### Required Services

Ensure the following services are running:

```bash
# Start all required services
docker compose -f docker-compose-noauth.yaml up -d
```

| Service     | Port | Purpose                      |
| ----------- | ---- | ---------------------------- |
| Gopie API   | 8000 | Dataset and project metadata |
| Chat Server | 8001 | Chat completion endpoint     |
| Qdrant      | 6333 | Vector database              |

### Required Environment Variables

For test case generation and running:

- Default configuration in `tests/test_config.py` works for local development

For DSPy-optimized evaluation:

- `OPENAI_API_KEY` - Required for LLM evaluation

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### Install Dependencies

```bash
cd chat-server
uv sync --dev
```

## Files

| File                     | Purpose                                   |
| ------------------------ | ----------------------------------------- |
| `test_case_generator.py` | Generate test cases from project datasets |
| `test_case_runner.py`    | Run tests and evaluate responses          |
| `test_case_labeler.html` | Web UI for manual labeling                |
| `golden_dataset_*.json`  | Generated test cases                      |
| `labeled_golden.json`    | Human-labeled ground truth                |

## Quick Start

### 1. Generate Test Cases

First, you need existing projects with datasets in Gopie. Get your project IDs from the Gopie UI or API.

```bash
# Generate test cases for specific projects
python -m tests.chat_server_tests.test_case_generator \
  --project-ids=project-id-1,project-id-2 \
  --type=both

# Generate only single dataset test cases
python -m tests.chat_server_tests.test_case_generator \
  --project-ids=project-id-1 \
  --type=single

# Generate only multi-dataset test cases
python -m tests.chat_server_tests.test_case_generator \
  --project-ids=project-id-1 \
  --type=multi
```

**Output:** `output/golden_dataset_{timestamp}.json`

### 2. Run Evaluation

```bash
# Run with manual evaluator (default)
python -m tests.chat_server_tests.test_case_runner

# Run with DSPy optimized evaluator (requires prior optimization)
python -m tests.chat_server_tests.test_case_runner --use-dspy

# Filter by data type
python -m tests.chat_server_tests.test_case_runner --data-type=single

# Filter by query type
python -m tests.chat_server_tests.test_case_runner --query-type=data

# Combine filters
python -m tests.chat_server_tests.test_case_runner --data-type=multi --query-type=viz
```

**Output:** `output/golden_dataset_*_results_run_{timestamp}.json`

### 3. Manual Labeling (Optional)

Open `test_case_labeler.html` in a browser to:

- Review test results with rendered visualizations
- Assign Pass/Partial/Fail labels with feedback
- Export labeled data for DSPy optimization

### 4. Optimize Evaluator (Optional)

Train a DSPy-optimized evaluator using labeled data:

```bash
# Requires labeled_golden.json
python -m tests.dspy.optimize_evaluator
```

## Test Case Format

### Input Format (generated)

```json
{
  "query": "What is the total revenue by region?",
  "project_id": "uuid-of-project",
  "dataset_id": "uuid-of-dataset",
  "query_type": "data",
  "data_type": "single",
  "expected_dataset_id": []
}
```

### Output Format (after evaluation)

```json
{
  "query": "What is the total revenue by region?",
  "project_id": "uuid-of-project",
  "dataset_id": "uuid-of-dataset",
  "query_type": "data",
  "data_type": "single",
  "chat_server_response": {
    "final_response": "Based on the analysis...",
    "selected_datasets": ["dataset_name"],
    "generated_sql_queries": ["SELECT region, SUM(revenue)..."],
    "tool_messages": [...],
    "visualization_results": []
  },
  "ai_evaluation": {
    "score": 8.5,
    "reasoning": "The response correctly...",
    "summary": "Pass - accurate SQL generation"
  },
  "request_time": 3.45
}
```

## Scoring

| Score | Label   | Meaning                       |
| ----- | ------- | ----------------------------- |
| 8-10  | Pass    | Correct and complete response |
| 5-7   | Partial | Acceptable but has issues     |
| 0-4   | Fail    | Incorrect or incomplete       |

### Evaluation Criteria

**For Data Queries:**

- SQL correctness and accuracy
- Proper dataset selection (for multi-dataset)
- Complete and relevant response

**For Visualization Queries:**

- Appropriate chart type selection
- Correct data mapping
- Valid Vega-Lite specification

## Command Reference

### test_case_generator.py

```bash
python -m tests.chat_server_tests.test_case_generator --help

Options:
  --project-ids    Comma-separated list of project IDs (required)
  --type           Test type: single, multi, or both (default: both)
```

### test_case_runner.py

```bash
python -m tests.chat_server_tests.test_case_runner --help

Options:
  --data-type      Filter: single or multi
  --query-type     Filter: data or viz
  --use-dspy       Use DSPy optimized evaluator
```

## Output Directory

All outputs are saved to `tests/chat_server_tests/output/`:

```
output/
├── golden_dataset_20250115_103045.json           # Generated test cases
├── golden_dataset_20250115_103045_results_run_20250115_110022.json  # Evaluation results
├── performance_history.json                       # Performance tracking
└── ...
```

## Integration with Performance Tools

Evaluation results are automatically tracked. View performance history:

```bash
# List all runs
python -m tests.performance_tools.compare_runs list

# Compare runs
python -m tests.performance_tools.compare_runs compare

# Find best run by metric
python -m tests.performance_tools.compare_runs best avg_score
```

See [performance_tools/README.md](../performance_tools/README.md) for more details.
