from datetime import datetime

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import QueryResult
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.types import State
from app.workflow.prompts.prompt_selector import get_prompt


async def generate_subqueries(state: State, config: RunnableConfig):
    messages = state.get("messages", [])

    if messages and isinstance(messages[-1], HumanMessage):
        user_input = str(messages[-1].content)
    else:
        raise Exception("Last Message must be a user message")

    query_result_object = QueryResult(
        original_user_query=user_input,
        timestamp=datetime.now(),
        execution_time=0,
        subqueries=[],
    )

    try:
        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": "do not stream",
            },
        )

        assessment_prompt = get_prompt(
            "assess_query_complexity", user_input=user_input
        )
        llm = get_llm_for_node("generate_subqueries", config)
        assessment_response = await llm.ainvoke(
            {
                "input": assessment_prompt,
                "chat_history": get_chat_history(config),
            }
        )

        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": "continue streaming",
            },
        )

        parser = JsonOutputParser()
        assessment_parsed = parser.parse(str(assessment_response.content))

        needs_breakdown = assessment_parsed.get("needs_breakdown", False)
        explanation = assessment_parsed.get("explanation", "")

        subqueries = []

        if needs_breakdown:
            subqueries_prompt = get_prompt(
                "generate_subqueries", user_input=user_input
            )
            subqueries_response = await llm.ainvoke(
                {
                    "input": subqueries_prompt,
                    "chat_history": get_chat_history(config),
                }
            )

            subqueries_parsed = parser.parse(str(subqueries_response.content))
            subqueries = subqueries_parsed.get("subqueries", [])

            subqueries_message = (
                "I'll break down your query into steps to give you "
                "a more complete answer:"
            )

            for i, subquery in enumerate(subqueries, 1):
                subqueries_message += f"\n\nStep {i}: {subquery}"

            await adispatch_custom_event(
                "dataful-agent",
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
