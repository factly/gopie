import json
import os

import pytest
import requests
from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .multi_dataset_cases import MULTI_DATASET_TEST_CASES
from .single_dataset_cases import SINGLE_DATASET_TEST_CASES
from .terminal_formatter import TerminalFormatter

load_dotenv()

URL = "http://localhost:8001/api/v1/chat/completions"


def create_chain():
    evaluation_prompt = ChatPromptTemplate.from_template("""
You are an expert evaluator for AI-generated SQL queries and data analysis results.

Given a user question and the output from an AI agent, evaluate the response on the following criteria:

1. **Accuracy (0-10)**: How accurate is the final answer to the user's question?
2. **SQL Quality (0-10)**: How well-written and appropriate are the generated SQL queries?
3. **Dataset Selection (0-10)**: How appropriate was the dataset selection for the query?
4. **Overall Performance (0-10)**: Overall assessment of the response quality

Please provide a brief explanation for each score.

**User Question**: {user_question}

**AI Agent Output**: {ai_output}

Please respond in the following JSON format:
{{
    "accuracy": <score>,
    "sql_quality": <score>,
    "dataset_selection": <score>,
    "overall_performance": <score>,
    "explanation": "Brief explanation of the evaluation"
}}
""")

    llm = ChatOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),  # type: ignore
        base_url=os.getenv("OPENROUTER_BASE_URL"),
        model="google/gemini-2.5-flash",
        streaming=True,
    )

    return evaluation_prompt | llm | JsonOutputParser()


def get_user_query(test_case):
    if "messages" in test_case:
        for message in test_case["messages"]:
            if message.get("role") == "user":
                return message.get("content", "")
    return test_case.get("query", "")


async def send_chat_request(test_case):
    headers = {"Content-Type": "application/json"}
    data = test_case.copy()
    if "expected_result" in data:
        del data["expected_result"]

    try:
        response = requests.post(URL, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


async def process_test_case(test_case, evaluation_chain, formatter=None, test_num=None, total_tests=None):
    user_query = get_user_query(test_case)

    if formatter and test_num and total_tests:
        formatter.print_test_case_header(test_num, total_tests, user_query)

    try:
        response = await send_chat_request(test_case)
        expected_result = test_case.get("expected_result", {})

        if "error" in response:
            if expected_result.get("error_expected") or expected_result.get("execution_failure"):
                result = {
                    "query": user_query,
                    "expected_dataset": test_case.get("expected_dataset", "N/A"),
                    "response": response,
                    "evaluation": {"note": "Expected error test case - passed"},
                    "status": "success"
                }
                if formatter:
                    formatter.print_success("Expected error test completed successfully")
                return result
            else:
                raise Exception(response["error"])

        if expected_result.get("error_expected") or expected_result.get("execution_failure"):
            raise Exception("Expected error but API call succeeded")

        if formatter:
            formatter.print_processing_status("Evaluating response...")

        ai_output = json.dumps(response, indent=2)
        evaluation = await evaluation_chain.ainvoke({
            "user_question": user_query,
            "ai_output": ai_output
        })

        result = {
            "query": user_query,
            "expected_dataset": test_case.get("expected_dataset", "N/A"),
            "response": response,
            "evaluation": evaluation,
            "status": "success"
        }

        if formatter:
            formatter.print_success("Test completed successfully")

        return result

    except Exception as e:
        error_result = {
            "query": user_query,
            "expected_dataset": test_case.get("expected_dataset", "N/A"),
            "error": str(e),
            "status": "error"
        }

        if formatter:
            formatter.print_error(f"Test failed: {str(e)}")

        return error_result


async def run_test_suite(test_cases, test_type, evaluation_chain, use_formatter=True):
    formatter = TerminalFormatter(use_colors=True) if use_formatter else None

    if formatter:
        formatter.print_header(f"Running {test_type} tests")
        formatter.print_info(f"Total test cases: {len(test_cases)}")

    results = []
    for i, test_case in enumerate(test_cases, 1):
        result = await process_test_case(
            test_case, evaluation_chain, formatter, i, len(test_cases)
        )
        results.append(result)

    if formatter:
        successful = len([r for r in results if r["status"] == "success"])
        failed = len([r for r in results if r["status"] == "error"])

        formatter.print_separator()
        formatter.print_info(f"Test Summary: {successful} passed, {failed} failed out of {len(results)} total")

        if failed == 0:
            formatter.print_success("All tests passed!")
        else:
            formatter.print_warning(f"{failed} tests failed")

    return results


@pytest.mark.asyncio
async def test_single_dataset_cases(request, capfd):
    evaluation_chain = create_chain()
    use_formatter = not request.config.getoption("--disable-formatter")

    if use_formatter:
        with capfd.disabled():
            results = await run_test_suite(
                SINGLE_DATASET_TEST_CASES, "single dataset", evaluation_chain, use_formatter
            )
    else:
        results = await run_test_suite(
            SINGLE_DATASET_TEST_CASES, "single dataset", evaluation_chain, use_formatter
        )

    failed_tests = [r for r in results if r["status"] == "error"]
    if failed_tests:
        pytest.fail(f"{len(failed_tests)} tests failed")


@pytest.mark.asyncio
async def test_multi_dataset_cases(request, capfd):
    evaluation_chain = create_chain()
    use_formatter = not request.config.getoption("--disable-formatter")

    if use_formatter:
        with capfd.disabled():
            results = await run_test_suite(
                MULTI_DATASET_TEST_CASES, "multi dataset", evaluation_chain, use_formatter
            )
    else:
        results = await run_test_suite(
            MULTI_DATASET_TEST_CASES, "multi dataset", evaluation_chain, use_formatter
        )

    failed_tests = [r for r in results if r["status"] == "error"]
    if failed_tests:
        pytest.fail(f"{len(failed_tests)} tests failed")


@pytest.mark.asyncio
async def test_all_cases(request, capfd):
    evaluation_chain = create_chain()
    use_formatter = not request.config.getoption("--disable-formatter")
    all_cases = SINGLE_DATASET_TEST_CASES + MULTI_DATASET_TEST_CASES

    if use_formatter:
        with capfd.disabled():
            results = await run_test_suite(
                all_cases, "all", evaluation_chain, use_formatter
            )
    else:
        results = await run_test_suite(
            all_cases, "all", evaluation_chain, use_formatter
        )

    failed_tests = [r for r in results if r["status"] == "error"]
    if failed_tests:
        pytest.fail(f"{len(failed_tests)} tests failed")