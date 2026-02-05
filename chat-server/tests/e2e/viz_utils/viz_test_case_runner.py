import argparse
import ast
import asyncio
import base64
import io
import json
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

import altair as alt
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from PIL import Image
from pydantic import BaseModel, Field

from app.core.constants import SQL_QUERIES_GENERATED, SQL_QUERIES_GENERATED_ARG
from app.utils.model_registry.model_provider import get_configured_llm_for_node

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.session import SingletonAiohttp
from tests.e2e.utils.test_utils import send_chat_request
from tests.e2e.viz_utils.io_utils import VizIOManager
from tests.test_config import TestConfig

CHAT_SERVER_URL = TestConfig.CHAT_SERVER_URL
VIZ_OUTPUT_DIR = Path(TestConfig.VIZ_OUTPUT_DIR)
IO = VizIOManager(VIZ_OUTPUT_DIR)

S3_ENDPOINT = TestConfig.S3_ENDPOINT_URL
S3_ACCESS_KEY = TestConfig.S3_ACCESS_KEY_ID
S3_SECRET_KEY = TestConfig.S3_SECRET_ACCESS_KEY
S3_BUCKET = TestConfig.S3_BUCKET_NAME
S3_REGION = TestConfig.S3_REGION


class VizEvaluationSchema(BaseModel):
    passed: bool = Field(description="Whether the generated chart matches the reference")
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Similarity score between 0 and 1 (higher is better)",
    )
    reasoning: str = Field(description="Short explanation of the judgment")


def _normalize_viz_url(url: str) -> str:
    parsed = urlparse(url)
    netloc = parsed.netloc
    if netloc.startswith("host.docker.internal"):
        new_netloc = netloc.replace("host.docker.internal", "localhost")
        parsed = parsed._replace(netloc=new_netloc)
    return urlunparse(parsed)


def _to_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


async def _llm_evaluate_images(reference: Image.Image, generated: Image.Image) -> dict[str, Any]:
    ref_data_url = _to_data_url(reference)
    gen_data_url = _to_data_url(generated)

    system = SystemMessage(
        content=(
            "You are a strict visualization QA assistant. Compare a reference chart to a generated chart. "
            "Judge if they match in: chart type, marks, axes/encodings (x,y,color,size), aggregations, binning, "
            "sorting, scales, legends, titles, and overall patterns/trends."
        )
    )
    human = HumanMessage(
        content=[
            {
                "type": "text",
                "text": (
                    "Compare these two charts. Return strict JSON with keys: "
                    "passed (boolean), score (float 0-1), reasoning (short string)."
                ),
            },
            {"type": "image_url", "image_url": {"url": ref_data_url, "detail": "auto"}},
            {"type": "image_url", "image_url": {"url": gen_data_url, "detail": "auto"}},
        ]
    )

    llm = get_configured_llm_for_node(
        node_name="identify_datasets", config=RunnableConfig(), schema=VizEvaluationSchema
    )
    resp = await llm.ainvoke([system, human])
    return resp.model_dump()


def _format_request_from_case(case: dict[str, Any]) -> dict[str, Any]:
    """
    Create the request payload expected by the chat server from a test case.
    """

    query_text = case.get("query", "")
    sql_queries = case.get("sql_queries", []) or []

    instructions = """
Additional instructions:
- This is a visualization request. No new data is required.
- Directly generate the visualization using the provided datasets.
- Use the SQL queries below to retrieve the full dataset(s) before visualizing.
- Focus on chart type, encodings, and sorting.
    """

    user_content = f"{query_text}{instructions}"

    ai_tool_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "tool_0_sql_queries_generated",
                "type": "function",
                "function": {
                    "name": SQL_QUERIES_GENERATED,
                    "arguments": json.dumps({SQL_QUERIES_GENERATED_ARG: sql_queries}),
                },
            }
        ],
    }

    formatted = {
        "messages": [ai_tool_message, {"role": "user", "content": user_content}],
        "model": "test",
        "user": "viz_test",
        "stream": True,
    }
    metadata = {}
    dataset_id = case.get("dataset_id")
    project_id = case.get("project_id")
    if dataset_id:
        metadata["dataset_id"] = dataset_id
    if project_id:
        metadata["project_id"] = project_id
    if metadata:
        formatted["metadata"] = metadata
    return formatted


def generate_image_from_altair_config(
    config: dict[str, Any],
) -> tuple[Optional[Image.Image], Optional[str]]:
    try:
        if "facet" in config or "spec" in config:
            chart = alt.FacetChart.from_dict(config)
        elif "hconcat" in config:
            chart = alt.HConcatChart.from_dict(config)
        elif "vconcat" in config:
            chart = alt.VConcatChart.from_dict(config)
        elif "concat" in config:
            chart = alt.ConcatChart.from_dict(config)
        elif "layer" in config:
            chart = alt.LayerChart.from_dict(config)
        else:
            chart = alt.Chart.from_dict(config)

        out_path = IO.save_chart_image(chart, subdir="generated_images", prefix="altair")
        return Image.open(out_path).convert("RGB"), str(out_path)
    except Exception as e:
        print(f"Failed to render image from Altair config: {e}")
        return None, None


async def run_viz_test_case(case: dict[str, Any]) -> dict[str, Any]:
    request_payload = _format_request_from_case(case)
    try:
        response = await send_chat_request(request_payload, CHAT_SERVER_URL)
    except Exception as e:
        return {
            "success": False,
            "error": f"Chat request failed: {e}",
            "evaluation": {"score": 0, "reasoning": "Chat request failed"},
        }

    # Get visualization URL from results
    viz_results = response.get("visualization_results", [])
    if not viz_results:
        return {
            "success": False,
            "error": "No visualization results returned by system",
            "evaluation": {"score": 0, "reasoning": "No visualization results"},
        }

    try:
        viz_data = (
            ast.literal_eval(viz_results[0]) if isinstance(viz_results[0], str) else viz_results[0]
        )
        viz_url = viz_data.get("json_path", "")
    except (ValueError, SyntaxError):
        return {
            "success": False,
            "error": "Failed to parse visualization result",
            "evaluation": {"score": 0, "reasoning": "Invalid visualization result format"},
        }

    if not viz_url:
        return {
            "success": False,
            "error": "No visualization URL found in results",
            "evaluation": {"score": 0, "reasoning": "No visualization URL"},
        }

    gen_url = _normalize_viz_url(viz_url)
    gen_img_path: Optional[str] = None
    try:
        json_config = IO.get_json_from_s3_url(
            gen_url,
            endpoint_url=S3_ENDPOINT,
            access_key=S3_ACCESS_KEY,
            secret_key=S3_SECRET_KEY,
            bucket=S3_BUCKET,
            region=S3_REGION,
        )
        gen_img, gen_img_path = generate_image_from_altair_config(json_config)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to render visualization JSON: {e}",
            "evaluation": {"score": 0, "reasoning": "Rendering failure"},
            "generated_url": gen_url,
        }

    ref_path = IO.resolve_path(case.get("image_path", ""))
    ref_img = IO.open_image(ref_path)
    if ref_img is None:
        print(f"Failed to open local image {ref_path}")

    if gen_img is None or ref_img is None:
        return {
            "success": False,
            "error": "Failed to load generated or reference image",
            "evaluation": {"score": 0, "reasoning": "Image load failure"},
            "generated_url": gen_url,
            "reference_path": str(ref_path),
            "generated_image_path": gen_img_path or "",
        }

    eval_result = await _llm_evaluate_images(ref_img, gen_img)
    return {
        "success": True,
        "evaluation": eval_result,
        "generated_url": gen_url,
        "reference_path": str(ref_path),
        "generated_image_path": gen_img_path,
    }


def _build_result_item(case: dict[str, Any], res: dict[str, Any]) -> dict[str, Any]:
    evaluation = res.get("evaluation", {})
    return {
        "project_id": case.get("project_id", ""),
        "dataset_id": case.get("dataset_id", ""),
        "query": case.get("query", ""),
        "sql_queries": case.get("sql_queries", []),
        "image_path": case.get("image_path", ""),
        "generated_image_path": res.get("generated_image_path", ""),
        "evaluation": evaluation,
        "success": res.get("success", False),
        "error": res.get("error", ""),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run visualization test cases")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="If provided, only run the first N cases",
    )
    args = parser.parse_args()

    try:
        num_deleted = IO.delete_existing_results_files()
        IO.clear_generated_images_dir()
        if num_deleted:
            print(f"Removed {num_deleted} previous results file(s).")
        print("Cleared generated images directory.")
    except Exception as e:
        print(f"Warning: failed to clean previous artifacts: {e}")

    latest = VizIOManager(VIZ_OUTPUT_DIR).find_latest_viz_json()
    if latest is None:
        print("No viz test cases JSON found. Generate using per_example_workflow.py")
        sys.exit(1)

    print(f"Using visualization dataset (JSON): {latest}")
    data = IO.load_json(latest)
    cases = list(data) if isinstance(data, list) else []
    if not cases:
        print("No test cases loaded from JSON")
        sys.exit(1)

    if args.limit is not None:
        cases = cases[: args.limit]

    total = len(cases)
    print(f"Running {total} visualization test case(s) ...")
    results_json_path = IO.results_json_path_for(latest)
    print(f"Writing results to: {results_json_path}")

    all_results: list[dict[str, Any]] = []

    try:
        for i, case in enumerate(cases, 1):
            print(f"[{i}/{total}] Query: {case.get('query','')[:80]}")
            res = await run_viz_test_case(case)
            evaluation = res.get("evaluation", {})
            if res.get("success") and isinstance(evaluation, dict):
                score = evaluation.get("score", 0)
                status = "PASS" if score >= 8 else "FAIL"
                print(f"  -> {status} (score={score}/10)")
            else:
                print(f"  -> ERROR: {res.get('error','Unknown error')}")
            all_results.append(_build_result_item(case, res))
    finally:
        await SingletonAiohttp.close_aiohttp_client()

    passed = 0
    failed = 0
    for item in all_results:
        evaluation = item.get("evaluation", {})
        if item.get("success") and isinstance(evaluation, dict) and evaluation.get("score", 0) >= 8:
            passed += 1
        else:
            failed += 1

    print(f"Evaluation complete. Passed: {passed}/{total}, Failed: {failed}/{total}")

    try:
        IO.save_json(results_json_path, all_results)
        print(f"Wrote results JSON: {results_json_path}")
    except Exception as e:
        print(f"Warning: failed to write results JSON: {e}")


if __name__ == "__main__":
    asyncio.run(main())
