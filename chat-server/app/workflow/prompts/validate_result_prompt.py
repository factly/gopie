from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.workflow.graph.single_dataset_graph.types import (
    SingleDatasetQueryResult,
)
from app.workflow.prompts.formatters.single_query_result import (
    format_single_query_result,
)


def create_validate_result_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """You are an expert query result validator. Your task is to analyze query results and determine if they adequately answer the user's original question.

WHAT YOU'LL RECEIVE:
- Original user query
- Query results (successful SQL queries, failed queries, errors, non-SQL responses)
- Dataset context

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

RESPONSE FORMAT (JSON only):
{{
    "is_valid": true/false,
    "reasoning": "Clear analysis explaining your decision - what works, what doesn't, and why",
    "confidence": 0.0-1.0,
    "missing_elements": ["specific items missing if invalid"],
    "recommendation": "respond_to_user" or "rerun_query"
}}

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
    prev_query_result: SingleDatasetQueryResult | None = None,
    **kwargs,
) -> dict:
    if not prev_query_result:
        return {"input": "❌ No query result provided for validation"}

    formatted_query_result = format_single_query_result(prev_query_result)

    return {"input": formatted_query_result}
