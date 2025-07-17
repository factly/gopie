from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.query import QueryResult
from app.workflow.prompts.formatters.format_query_result import format_query_result


def create_validate_result_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """You are an expert query result validator. Your task is to analyze query results and determine if they adequately answer the user's original question.

WHAT YOU'LL RECEIVE:
- Query type (single_dataset or multi_dataset)
- Original user query
- Query results (successful SQL queries, failed queries, errors, non-SQL responses)
- Dataset context

NOTE:
    Visualization is not processed by this agent, it is processed by another agent.
    So, don't focuse on visualization not being present in the results.

YOUR VALIDATION PROCESS:
1. Compare the user's intent with what the results actually provide
2. Assess data quality, completeness, and relevance
3. Evaluate if failed queries prevent answering the question
4. Consider if partial results still provide meaningful insights

VALIDATION DECISION CRITERIA:
✅ MARK AS VALID when:
- Results directly answer the user's question (even if partial)
- Data is relevant and provides meaningful insights
- Any failures don't prevent a useful response
- User can get value from the available information

❌ MARK AS INVALID when:
- Critical queries failed, preventing any useful answer
- Results don't address the user's actual question
- Data quality issues make results unreliable
- Missing essential information that user specifically requested

CONFIDENCE SCORING (be precise):
- 0.9-1.0: Very high confidence - excellent results
- 0.7-0.9: High confidence - good results, minor improvements possible
- 0.4-0.6: Medium confidence - some issues, improvements recommended
- 0.0-0.3: Low confidence - major issues, significant improvements needed

RECOMMENDATION FIELD (choose the most appropriate):
- If you are validating a **single_dataset** result, only use:
    - "pass_on_results": Results are sufficient to answer the user's question.
    - "rerun_query": Minor issues detected; retrying the query may help.
- If you are validating a **multi-dataset** result, you only use the following recommendations:
    - "replan": The query logic or approach needs to be changed (not just retried).
    - "reidentify_datasets": The selected datasets are wrong, insufficient, or do not match the user's intent; new datasets should be identified.
    - "route_response": Results are sufficient to answer the user's question.

RESPONSE FORMAT (JSON only):
{
    "is_valid": true/false,
    "reasoning": "Clear analysis explaining your decision - what works, what doesn't, and why",
    "confidence": 0.0-1.0,
    "missing_elements": ["specific items missing if invalid"],
    "recommendation": "pass_on_results" | "rerun_query" | "replan" | "reidentify_datasets" | "route_response"
}

KEY PRINCIPLE: Focus on whether the user can get meaningful value from these results, not perfection."""

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
    if not prev_query_result:
        return {"input": "❌ No query result provided for validation"}

    formatted_query_result = format_query_result(prev_query_result)

    if prev_query_result.single_dataset_query_result:
        heading = "=== VALIDATING SINGLE DATASET RESULT ==="
    else:
        heading = "=== VALIDATING MULTI-DATASET RESULT ==="

    input_with_heading = f"{heading}\n\n{formatted_query_result}"

    return {"input": input_with_heading}
