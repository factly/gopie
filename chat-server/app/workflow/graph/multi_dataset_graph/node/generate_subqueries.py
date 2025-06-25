from datetime import datetime

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import QueryResult
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_model_provider,
)
from app.workflow.graph.multi_dataset_graph.types import State


async def generate_subqueries(state: State, config: RunnableConfig):
    user_input = state.get("user_query", "")

    query_result_object = QueryResult(
        original_user_query=user_input,
        timestamp=datetime.now(),
        execution_time=0,
        subqueries=[],
    )

    try:
        assessment_prompt = get_prompt(
            "assess_query_complexity",
            user_input=user_input,
            chat_history=get_chat_history(config),
        )
        llm = get_model_provider(config).get_llm_for_node(
            "generate_subqueries"
        )
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
                chat_history=get_chat_history(config),
            )
            subqueries_response = await llm.ainvoke(subqueries_prompt)

            subqueries_parsed = parser.parse(str(subqueries_response.content))
            subqueries = subqueries_parsed.get("subqueries", [])

            subqueries_message = (
                "I'll break down your query into steps to give you "
                "a more complete answer:"
            )

            for i, subquery in enumerate(subqueries, 1):
                subqueries_message += f"\n\nStep {i}: {subquery}"

            await adispatch_custom_event(
                "gopie-agent",
                {
                    "content": subqueries_message,
                },
            )

            if len(subqueries) > 3:
                subqueries = subqueries[:3]

            if not subqueries:
                subqueries = [user_input]
        else:
            subqueries = [user_input]

            await adispatch_custom_event(
                "gopie-agent",
                {
                    "content": "Analyzing query...",
                },
            )

        return {
            "user_query": user_input,
            "subquery_index": -1,
            "subqueries": subqueries,
            "query_result": query_result_object,
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

        return {
            "user_query": user_input,
            "subquery_index": -1,
            "subqueries": default_subqueries,
            "query_result": query_result_object,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }
