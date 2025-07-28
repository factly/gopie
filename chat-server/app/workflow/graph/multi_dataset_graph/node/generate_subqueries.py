from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.models.message import ErrorMessage, IntermediateStep
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_configured_llm_for_node
from app.workflow.graph.multi_dataset_graph.types import State


async def generate_subqueries(state: State, config: RunnableConfig):
    user_input = state.get("user_query", "")
    query_result = state.get("query_result")

    try:
        assessment_prompt = get_prompt(
            "assess_query_complexity",
            user_input=user_input,
        )
        llm = get_configured_llm_for_node("generate_subqueries", config)
        assessment_response = await llm.ainvoke(assessment_prompt)

        parser = JsonOutputParser()
        assessment_parsed = parser.parse(str(assessment_response.content))

        needs_breakdown = assessment_parsed.get("needs_breakdown", False)
        explanation = assessment_parsed.get("explanation", "")

        subqueries = []

        if needs_breakdown:
            subqueries_prompt = get_prompt(
                "generate_subqueries",
                user_input=user_input,
            )
            subqueries_response = await llm.ainvoke(subqueries_prompt)

            subqueries_parsed = parser.parse(str(subqueries_response.content))
            subqueries = subqueries_parsed.get("subqueries", [])

            subqueries_message = (
                "I'll break down your query into steps to give you a more complete answer:"
            )

            for i, subquery in enumerate(subqueries, 1):
                subqueries_message += f"\n\nStep {i}: {subquery}"

            subqueries_message += "\n\nPlease wait while I process these steps."

            await adispatch_custom_event(
                "gopie-agent",
                {
                    "content": subqueries_message,
                },
            )

            if len(subqueries) > 2:
                subqueries = subqueries[:2]

            if not subqueries:
                subqueries = [user_input]
        else:
            subqueries = [user_input]

            await adispatch_custom_event(
                "gopie-agent",
                {
                    "content": "Checking query complexity...",
                },
            )

        for subquery_text in subqueries:
            query_result.add_subquery(
                query_text=subquery_text,
                sql_queries=[],
                tables_used=None,
            )

        return {
            "user_query": user_input,
            "subquery_index": 0,
            "subqueries": subqueries,
            "query_result": query_result,
            "messages": [
                IntermediateStep.from_json(
                    {
                        "needs_breakdown": needs_breakdown,
                        "subqueries": subqueries,
                        "original_query": user_input,
                        "explanation": explanation,
                    },
                )
            ],
        }
    except Exception as e:
        error_msg = f"Error in subquery generation: {e!s}"
        default_subqueries = [user_input]

        query_result.add_subquery(
            query_text=user_input,
            sql_queries=[],
            tables_used=None,
        )

        return {
            "user_query": user_input,
            "subquery_index": 0,
            "subqueries": default_subqueries,
            "query_result": query_result,
            "messages": [ErrorMessage(content=error_msg)],
        }
