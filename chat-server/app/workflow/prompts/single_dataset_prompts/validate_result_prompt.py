from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.query import QueryResult
from app.workflow.prompts.formatters.format_query_result import (
    format_query_result,
)


def create_validate_result_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    """
    Create a prompt for validating query results against the user's original question.

    This function generates a prompt that instructs an expert agent to validate query results,
    assess their adequacy and relevance, and provide recommendations for next steps.

    Args:
        **kwargs: Keyword arguments containing:
            prompt_template (bool, optional): If True, returns a ChatPromptTemplate for
                dynamic input; otherwise, returns a list of message objects. Defaults to False.
            input (str, optional): The input content to be validated. Defaults to "".

    Returns:
        list[BaseMessage] | ChatPromptTemplate: Either a list of message objects or a
            ChatPromptTemplate for result validation.
    """
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are an expert query result validator responsible for analyzing query results and
determining if they adequately answer the user's original question.

INPUT CONTEXT:
You will receive:
- Query type (single_dataset or multi_dataset)
- Original user query
- Query results (successful SQL queries, failed queries, errors, non-SQL responses)
- Dataset context

IMPORTANT NOTES:
- Visualization processing is handled by a separate agent - do not focus on missing visualizations
- Only validate executed subqueries - ignore unprocessed subqueries
- Focus on the portion of the user query that has been executed

VALIDATION PROCESS:
1. Compare user intent with actual results provided
2. Assess data quality, completeness, and relevance
3. Evaluate if failed queries prevent answering the question
4. Consider if partial results still provide meaningful insights
5. Identify improvements needed to enhance results or fix issues
6. Include sufficient context from query results to make response helpful

VALIDATION CRITERIA:

MARK AS VALID when:
- Results directly answer the user's question (even if partial)
- Data is relevant and provides meaningful insights
- Any failures don't prevent a useful response
- User can derive value from available information

MARK AS INVALID when:
- Critical queries failed, preventing any useful answer
- Results don't address the user's actual question
- Data quality issues make results unreliable
- Missing essential information specifically requested by user

RECOMMENDATION OPTIONS:

For SINGLE_DATASET results:
- "pass_on_results": Results are sufficient to answer the user's question
- "rerun_query": Minor issues detected; retrying the query may help

For MULTI-DATASET results:
- "replan": Query logic or approach needs to be changed (not just retried)
- "reidentify_datasets": Selected datasets are wrong, insufficient, or don't match user intent
- "route_response": Results are sufficient to answer the user's question

CORE PRINCIPLE:
Focus on whether the user can get meaningful value from these results rather than
seeking perfection. Provide actionable, concise reasoning and clear next steps.
"""

    human_template_str = "{input}"

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(input=input_content)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]


def format_validate_result_input(
    prev_query_result: QueryResult | None = None,
    **kwargs,
) -> dict:
    """
    Prepare the input string for a query result validation prompt, including a heading indicating single or multi-dataset context.

    If no previous query result is provided, returns a message indicating that validation cannot proceed. Otherwise, formats the query result and prepends a heading specifying whether it is a single or multi-dataset result.

    Returns:
        dict: A dictionary with the key "input" containing the formatted prompt input string.
    """
    if not prev_query_result:
        return {"input": "❌ No query result provided for validation"}

    formatted_query_result = format_query_result(prev_query_result)

    if prev_query_result.single_dataset_query_result:
        heading = "=== VALIDATING SINGLE DATASET RESULT ==="
    else:
        heading = "=== VALIDATING MULTI-DATASET RESULT ==="

    input_with_heading = f"{heading}\n\n{formatted_query_result}"

    return {"input": input_with_heading}
