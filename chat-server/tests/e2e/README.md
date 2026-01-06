# E2E Test Suite

End-to-end tests for the GoPie Chat Server. These tests verify complete workflows by interacting with real services.

## Prerequisites

Before running E2E tests, ensure you have:

1. **Python 3.11+** installed
2. **Docker & Docker Compose** installed
3. **uv** package manager: `pip install uv`
4. **Dependencies installed**: `uv sync --dev`

## Required Services

E2E tests require the following services running:

| Service     | Port | Purpose                     |
| ----------- | ---- | --------------------------- |
| Gopie API   | 8000 | Main API server             |
| Chat Server | 8001 | Chat completion endpoint    |
| Qdrant      | 6333 | Vector database             |
| MinIO (S3)  | 9000 | Object storage for datasets |

### Starting Services

```bash
# From the chat-server directory
docker compose -f docker-compose-noauth.yaml up -d

# Verify services are running
docker compose -f docker-compose-noauth.yaml ps
```

## Environment Configuration

E2E tests use settings from `tests/test_config.py`. Default values work for local development:

```python
GOPIE_API_URL = "http://localhost:8000"
CHAT_SERVER_URL = "http://localhost:8001/api/v1/chat/completions"
S3_ENDPOINT_URL = "http://localhost:9000"
S3_ACCESS_KEY_ID = "minioadmin"
S3_SECRET_ACCESS_KEY = "minioadmin"
S3_BUCKET_NAME = "gopie"
```

## Test Files

### `test_e2e_script.py` - Data Query Tests

Tests SQL generation from natural language queries.

**What it tests:**

- Single dataset queries (filtering, aggregations, comparisons)
- Multi-dataset queries (JOINs, cross-dataset analytics)
- SQL generation accuracy
- Response quality scoring (0-10)

**Workflow:**

1. Creates a test project in Gopie
2. Uploads CSV files from `tests/e2e/datasets/` to S3
3. Ingests datasets into Gopie
4. Generates test queries based on schema
5. Runs queries against chat server
6. Evaluates response quality
7. Cleans up test project

### `test_viz_e2e.py` - Visualization Tests

Tests chart generation from Vega dataset examples.

**What it tests:**

- Chart generation requests
- Vega-Lite specification generation
- Visualization rendering accuracy

**Workflow:**

1. Downloads Vega example datasets
2. Uploads to test project
3. Converts chart images to queries
4. Validates generated visualizations

---

## Visualization Tests - Detailed Workflow

The visualization tests use a two-step process with separate scripts in `viz_utils/`:

### Step 1: Generate Test Cases with `per_example_workflow.py`

This script processes Altair/Vega-Lite example scripts and generates test cases:

```bash
# First, create a project with vega datasets uploaded
# (This can be done manually or with the replicate_prod_to_local script)

# Then run the per-example workflow
python -m tests.e2e.viz_utils.per_example_workflow \
  --project-id your-project-id \
  --output-dir tests/e2e/output/visualization
```

**What it does:**

1. Reads Python scripts from `viz_utils/examples_arguments_syntax/`
2. Executes each script to generate a reference chart image
3. Extracts dataset names from the code
4. Looks up datasets in the Gopie project
5. Uses LLM to generate a natural language query from the image
6. Runs the query against the chat server
7. Saves results to JSON

### Step 2: Run Test Cases with `viz_test_case_runner.py`

After generating test cases, run the test case runner to evaluate them:

```bash
python -m tests.e2e.viz_utils.viz_test_case_runner --limit 10
```

**What it does:**

1. Loads the latest test cases JSON from `per_example_workflow`
2. Sends each query to the chat server
3. Downloads the generated visualization
4. Uses LLM to compare reference vs generated charts
5. Outputs pass/fail results with similarity scores

### Required: `examples_arguments_syntax/` Folder

The visualization tests require Altair/Vega-Lite chart scripts that use `vega_datasets`:

```
tests/e2e/viz_utils/examples_arguments_syntax/
├── __init__.py              # Must export iter_examples_arguments_syntax()
├── bar_chart.py             # Chart scripts using vega_datasets
├── line_chart.py
├── scatter_plot.py
└── ...
```

> **📥 Required Setup:** Clone the Altair test scripts from:
> https://github.com/vega/altair/tree/main/tests/examples_arguments_syntax
> These scripts use `vega_datasets` (cars, stocks, iris, etc.) which are
> automatically uploaded to Gopie during the test workflow.

**Requirements for each script:**

1. Must have a docstring at the top (title and description)
2. Should include a `# category:` comment
3. Must assign the chart to a variable named `chart`
4. Use `vega_datasets` for data sources

### Complete Visualization Test Workflow

```bash
# 1. Start services
docker compose -f docker-compose-noauth.yaml up -d

# 2. Create a project with vega datasets
python -m tests.scripts.replicate_prod_to_local \
  --local-url http://localhost:8000 \
  --csv-folder tests/e2e/datasets \
  --project-name "Vega Test Project"

# 3. Add example scripts to examples_arguments_syntax/

# 4. Run per-example workflow to generate test cases
python -m tests.e2e.viz_utils.per_example_workflow \
  --project-id <your-project-id>

# 5. Run the test case runner
python -m tests.e2e.viz_utils.viz_test_case_runner

# 6. Or run via pytest
uv run pytest tests/e2e/test_viz_e2e.py -v
```

---

## Running Tests

### Run All E2E Tests

```bash
uv run pytest tests/e2e/ -v
```

### Run Data Query Tests Only

```bash
# All data query tests
uv run pytest tests/e2e/test_e2e_script.py -v

# Single dataset tests only
uv run pytest tests/e2e/test_e2e_script.py --type=single -v

# Multi dataset tests only
uv run pytest tests/e2e/test_e2e_script.py --type=multi -v
```

### Run Visualization Tests Only

```bash
# All visualization tests
uv run pytest tests/e2e/test_viz_e2e.py -v

# Limit number of test cases
uv run pytest tests/e2e/test_viz_e2e.py --limit=5 -v
```

### Additional Options

```bash
# Disable colorful output (for CI/logs)
uv run pytest tests/e2e/ --disable-formatter -v

# Run with specific test type
uv run pytest tests/e2e/test_e2e_script.py --type=all -v
```

## Adding Test Data

### For Data Query Tests

Place CSV files in the datasets folder:

```
tests/e2e/datasets/
├── your-dataset-1.csv
├── your-dataset-2.csv
└── ...
```

The test suite will:

1. Auto-detect CSV files in this folder
2. Upload them to MinIO S3
3. Ingest them into a test Gopie project
4. Generate test queries based on schema
5. Clean up after tests complete

### Sample Dataset Format

```csv
id,name,value,category,date
1,Item A,100.50,Category1,2024-01-15
2,Item B,200.75,Category2,2024-01-16
```

## Test Output

Results are saved to `tests/e2e/output/`:

```
tests/e2e/output/
└── visualization/
    ├── images/                    # Reference chart images
    │   ├── chart_20250106_*.png
    │   └── ...
    ├── generated_images/          # Generated chart images
    │   ├── altair_20250106_*.png
    │   └── ...
    ├── viz_test_cases_*.json      # Generated test cases
    └── viz_test_cases_*_results.json  # Evaluation results
```

### Visualization Test Output Format

**Test cases JSON (`viz_test_cases_*.json`):**

```json
{
  "example_name": "bar_chart",
  "status": "success",
  "image_path": "output/visualization/images/chart_*.png",
  "datasets": ["cars"],
  "project_id": "uuid",
  "dataset_id": "uuid",
  "query": "Create a bar chart showing count by Origin",
  "sql_queries": ["SELECT * FROM \"cars\""]
}
```

**Results JSON (`viz_test_cases_*_results.json`):**

```json
{
  "query": "Create a bar chart showing count by Origin",
  "evaluation": {
    "passed": true,
    "score": 0.85,
    "reasoning": "Charts match in type and encoding"
  },
  "success": true,
  "generated_image_path": "output/visualization/generated_images/altair_*.png"
}
```

---
