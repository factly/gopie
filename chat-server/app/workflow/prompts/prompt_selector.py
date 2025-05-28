from typing import Any, Literal, TypedDict, Union

from app.models.schema import DatasetSchema
from app.workflow.prompts.analyze_query_prompt import (
    create_analyze_query_prompt,
)
from app.workflow.prompts.generate_subqueries_prompt import (
    create_assess_query_complexity_prompt,
    create_generate_subqueries_prompt,
)
from app.workflow.prompts.identify_datasets_prompt import (
    create_identify_datasets_prompt,
)
from app.workflow.prompts.plan_query_prompt import create_query_prompt

NodeName = Literal[
    "plan_query",
    "identify_datasets",
    "analyze_query",
    "generate_subqueries",
    "assess_query_complexity",
]


class PlanQueryParams(TypedDict):
    user_query: str
    datasets_info: dict
    error_message: list[dict] | None
    attempt: int


class IdentifyDatasetsParams(TypedDict):
    user_query: str
    available_datasets_schemas: list[DatasetSchema]
    confidence_score: float | None
    query_type: str | None


class AnalyzeQueryParams(TypedDict):
    user_query: str
    tool_results: list[Any]


class GenerateSubqueriesParams(TypedDict):
    user_input: str


class AssessQueryComplexityParams(TypedDict):
    user_input: str


NodeParams = Union[
    PlanQueryParams,
    IdentifyDatasetsParams,
    AnalyzeQueryParams,
    GenerateSubqueriesParams,
    AssessQueryComplexityParams,
]


def get_prompt(node_name: NodeName, **kwargs) -> str:
    """
    Get the appropriate prompt for a workflow node based on the node name.

    Args:
        node_name: Name of the node to get a prompt for
        **kwargs: Parameters to pass to the prompt generation function

    Returns:
        A formatted prompt string for the specified node
    """
    prompt_map = {
        "plan_query": _get_plan_query_prompt,
        "identify_datasets": _get_identify_datasets_prompt,
        "analyze_query": _get_analyze_query_prompt,
        "generate_subqueries": _get_generate_subqueries_prompt,
        "assess_query_complexity": _get_assess_query_complexity_prompt,
    }

    if node_name not in prompt_map:
        raise ValueError(f"No prompt available for node: {node_name}")

    _validate_params(node_name, kwargs)

    return prompt_map[node_name](**kwargs)


def _validate_params(node_name: NodeName, params: dict[str, Any]) -> None:
    """
    Validate that all required parameters for a node are present.

    Args:
        node_name: The name of the node
        params: The parameters passed to the prompt function

    Raises:
        ValueError: If required parameters are missing
    """
    required_params = {
        "plan_query": ["user_query", "datasets_info"],
        "identify_datasets": [
            "user_query",
            "available_datasets_schemas",
            "confidence_score",
            "query_type",
        ],
        "analyze_query": ["user_query", "tool_results"],
        "generate_subqueries": ["user_input"],
        "assess_query_complexity": ["user_input"],
    }

    missing_params = [
        param for param in required_params[node_name] if param not in params
    ]

    if missing_params:
        error_msg = f"Missing required parameters for {node_name}: "
        error_msg += f"{', '.join(missing_params)}"
        raise ValueError(error_msg)


def _get_plan_query_prompt(
    user_query: str,
    datasets_info: dict,
    error_message: list[dict] | None = None,
    attempt: int = 1,
) -> str:
    return create_query_prompt(
        user_query=user_query,
        datasets_info=datasets_info,
        error_message=error_message,
        attempt=attempt,
    )


def _get_identify_datasets_prompt(
    user_query: str,
    available_datasets_schemas: list[DatasetSchema],
    confidence_score: float | None = None,
    query_type: str | None = None,
) -> str:
    return create_identify_datasets_prompt(
        user_query=user_query,
        available_datasets_schemas=available_datasets_schemas,
        confidence_score=confidence_score,
        query_type=query_type,
    )


def _get_analyze_query_prompt(user_query: str, tool_results: list[Any]) -> str:
    return create_analyze_query_prompt(
        user_query=user_query,
        tool_results=tool_results,
    )


def _get_generate_subqueries_prompt(user_input: str) -> str:
    return create_generate_subqueries_prompt(user_input=user_input)


def _get_assess_query_complexity_prompt(user_input: str) -> str:
    return create_assess_query_complexity_prompt(user_input=user_input)
