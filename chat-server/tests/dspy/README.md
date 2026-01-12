# DSPy Evaluator Optimization

Train and optimize an LLM-based evaluator using DSPy's few-shot learning capabilities.

## Overview

This module improves evaluation accuracy by training a DSPy-optimized evaluator on labeled test cases. The optimized evaluator provides more consistent and accurate scoring compared to the default manual evaluation chain.

## Prerequisites

### Required Environment Variables

```bash
# REQUIRED: OpenAI API key for DSPy
export OPENAI_API_KEY="your-openai-api-key"
```

### Install Dependencies

```bash
cd chat-server
uv sync --dev
```

### Labeled Training Data

You need labeled test cases for training. Create these by:

1. Running the test case generator
2. Running the test case runner
3. Using the manual labeler UI

The labeled data should be in `tests/chat_server_tests/labeled_golden.json`.

## Quick Start

### 1. Generate Labeled Data (if not already available)

```bash
# Generate test cases
python -m tests.chat_server_tests.test_case_generator --project-ids=your-project-id

# Run evaluation to get results
python -m tests.chat_server_tests.test_case_runner

# Use the labeler UI to create labeled data
open tests/chat_server_tests/test_case_labeler.html
```

### 2. Train the Optimized Evaluator

```bash
# Basic training (uses default settings)
python -m tests.dspy.optimize_evaluator

# With custom settings
python -m tests.dspy.optimize_evaluator \
  --dataset=tests/chat_server_tests/labeled_golden.json \
  --train-ratio=0.7 \
  --max-bootstrapped=8
```

**Output:** `output/optimized_evaluator_{timestamp}.json`

### 3. Use the Optimized Evaluator

```bash
# Run test case runner with DSPy evaluator
python -m tests.chat_server_tests.test_case_runner --use-dspy
```

## Files

| File                    | Purpose                                |
| ----------------------- | -------------------------------------- |
| `optimize_evaluator.py` | Train DSPy evaluator with labeled data |
| `evaluator.py`          | Load and use optimized evaluator       |
| `signatures.py`         | DSPy signature definitions             |
| `data_loader.py`        | Load and preprocess training data      |
| `output/`               | Saved optimized evaluators             |

## Command Reference

### optimize_evaluator.py

```bash
python -m tests.dspy.optimize_evaluator --help

Options:
  --dataset          Path to labeled dataset JSON file
                     (default: tests/chat_server_tests/labeled_golden.json)
  --train-ratio      Ratio of data to use for training (0.0-1.0)
                     (default: 0.7)
  --max-bootstrapped Maximum bootstrapped demos for optimization
                     (default: 8)
```

## Configuration

Settings are defined in `tests/test_config.py`:

```python
# DSPy Configuration
DEFAULT_LLM_MODEL = "gpt-4o"          # Model for evaluation
OPENAI_API_KEY = ""                    # Set via environment variable
DSPY_CACHE_DIR = "tests/dspy/.cache"   # Cache directory
DSPY_LOG_LEVEL = "INFO"                # Logging level
DSPY_OPTIMIZER_MODEL = "gpt-4o"        # Model for optimization
DSPY_MAX_BOOTSTRAPPED_DEMOS = 8        # Max bootstrap demos
DSPY_MAX_LABELED_DEMOS = 4             # Max labeled demos
```

## Labeled Data Format

The labeled data file should contain test cases with human-assigned scores:

```json
[
  {
    "query": "What is the total revenue by region?",
    "chat_server_response": {
      "final_response": "Based on the analysis...",
      "selected_datasets": ["revenue_data"],
      "generated_sql_queries": ["SELECT region, SUM(revenue)..."]
    },
    "human_label": {
      "score": 9,
      "label": "Pass",
      "feedback": "Correct SQL and accurate response"
    }
  }
]
```

## How It Works

1. **Load Training Data:** Reads labeled test cases from JSON file
2. **Preprocess:** Converts to DSPy-compatible format
3. **Bootstrap:** Uses examples to generate optimized prompts
4. **Optimize:** Finds the best prompt configuration
5. **Save:** Exports optimized evaluator to JSON

## Evaluation Metrics

The optimized evaluator provides:

| Field              | Type   | Description                     |
| ------------------ | ------ | ------------------------------- |
| `evaluation_score` | 0-10   | Quality score for the response  |
| `reasoning`        | string | Detailed evaluation reasoning   |
| `summary`          | string | Brief summary of the evaluation |

## Output Directory

Optimized evaluators are saved to `tests/dspy/output/`:

```
output/
├── optimized_evaluator_20250115_103045.json
├── optimized_evaluator_20250116_142233.json
└── ...
```

The test runner automatically uses the most recent evaluator file.
