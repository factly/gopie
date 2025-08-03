from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.query import QueryResult
from app.workflow.prompts.formatters.format_query_result import (
    format_query_result,
)


def create_validate_result_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    """
    Constructs a prompt for an expert agent to validate query results against a user's original question.

    Depending on the `prompt_template` argument, returns either a `ChatPromptTemplate` or a list of messages containing detailed validation instructions and the provided input. The prompt guides the agent to assess the adequacy, relevance, and quality of query results, assign a confidence score, and select an appropriate recommendation based on whether the query involved a single or multiple datasets. The agent's response is expected in a structured JSON format.
    """
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """You are an expert query result validator. Your task is to analyze query results and determine if they adequately answer the user's original question.

WHAT YOU'LL RECEIVE:
- Query type (single_dataset or multi_dataset)
- Original user query
- Query results (successful SQL queries, failed queries, errors, non-SQL responses)
- Dataset context

NOTE:
    - Visualization is not processed by this agent, it is processed by another agent.
    So, don't focus on visualization not being present in the results.
    - The subqueries which are not processed shouldn't be validated, just validate that part of the user query for which the subqueries are already executed.

YOUR VALIDATION PROCESS:
1. Compare the user's intent with what the results actually provide
2. Assess data quality, completeness, and relevance
3. Evaluate if failed queries prevent answering the question
4. Consider if partial results still provide meaningful insights

VALIDATION DECISION CRITERIA:
* MARK AS VALID when:
- Results directly answer the user's question (even if partial)
- Data is relevant and provides meaningful insights
- Any failures don't prevent a useful response
- User can get value from the available information

* MARK AS INVALID when:
- Critical queries failed, preventing any useful answer
- Results don't address the user's actual question
- Data quality issues make results unreliable
- Missing essential information that user specifically requested

RECOMMENDATION FIELD (choose the most appropriate):
- If you are validating a **single_dataset** result, only use:
    - "pass_on_results": Results are sufficient to answer the user's question.
    - "rerun_query": Minor issues detected; retrying the query may help.
- If you are validating a **multi-dataset** result, you only use the following recommendations:
    - "replan": The query logic or approach needs to be changed (not just retried).
    - "reidentify_datasets": The selected datasets are wrong, insufficient, or do not match the user's intent; new datasets should be identified.
    - "route_response": Results are sufficient to answer the user's question.

KEY PRINCIPLE: Focus on whether the user can get meaningful value from these results, not perfection. Your response should be actionable and concise, providing clear reasoning and next steps based on your analysis."""

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
