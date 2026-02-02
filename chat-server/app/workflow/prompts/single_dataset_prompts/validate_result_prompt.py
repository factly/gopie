from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.query import QueryResult
from app.workflow.prompts.formatters.format_query_result import (
    format_query_result,
)


def validate_result_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
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

IMPORTANT NOTES FOR MULTI-DATASET QUERIES:
- For multi-dataset queries, you are validating ONLY THE CURRENT SUBQUERY, not the entire user question
- Each subquery is a step toward answering the full user query
- Focus on whether THIS SPECIFIC SUBQUERY executed successfully and returned expected data
- Do NOT recommend replan/reidentify if the current subquery completed its task, even if it doesn't fully answer the original question
- Subsequent subqueries will build upon this result to answer the complete question
- Only recommend replan/reidentify if THIS SUBQUERY itself failed or returned wrong/incomplete data for its specific task

VALIDATION PROCESS:
1. For SINGLE-DATASET: Compare user intent with actual results provided
2. For MULTI-DATASET: Evaluate if the CURRENT SUBQUERY completed its specific task successfully
3. Assess data quality, completeness, and relevance for the subquery's purpose
4. Evaluate if failed queries prevent completing this subquery's specific goal
5. Consider if partial results still provide meaningful insights for this step
6. Identify improvements needed only if this specific subquery has issues

VALIDATION CRITERIA:

MARK AS VALID when:
- Results directly answer the user's question (single-dataset) OR complete the subquery's task (multi-dataset)
- Data is relevant and provides meaningful insights for the step
- Any failures don't prevent a useful response for this subquery
- Truncated SQL results are acceptable (due to large result sizes)

MARK AS INVALID when:
- Critical queries failed for THIS SUBQUERY, preventing its completion
- Results don't address this subquery's specific task
- Data quality issues make subquery results unreliable
- Missing essential information specifically required by this subquery

RECOMMENDATION OPTIONS:

For SINGLE_DATASET results:
- "pass_on_results": Results are sufficient to answer the user's question
- "rerun_query": Minor issues detected; retrying the query may help

For MULTI-DATASET results:
- "route_response": This subquery completed successfully (even if more subqueries are needed for full answer)
- "replan": THIS SUBQUERY's logic or approach needs to be changed
- "reidentify_datasets": Datasets selected for THIS SUBQUERY are wrong or insufficient

CORE PRINCIPLE:
For multi-dataset queries, validate the SUBQUERY execution, not the full user question.
If the subquery did its job, mark it as valid and route to response (allowing next subquery to continue).
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
