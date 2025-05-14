from datetime import datetime

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser

from app.core.langchain_config import get_llm_with_trace
from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import QueryResult
from app.workflow.graph.types import State
from app.workflow.prompts.prompt_selector import get_prompt


async def generate_subqueries(state: State):
    messages = state.get("messages", [])

    if messages and isinstance(messages[-1], HumanMessage):
        user_input = str(messages[-1].content)
    else:
        raise Exception("Last Message must be a user message")

    llm_prompt = get_prompt("generate_subqueries", user_input=user_input)

    llm = get_llm_with_trace(state.get("trace_id"))
    response = await llm.ainvoke({"input": llm_prompt})

    query_result_object = QueryResult(
        original_user_query=user_input,
        timestamp=datetime.now(),
        execution_time=0,
        subqueries=[],
    )

    try:
        parser = JsonOutputParser()
        parsed_content = parser.parse(str(response.content))

        needs_breakdown = parsed_content.get("needs_breakdown", False)
        explanation = parsed_content.get("explanation", "")

        if needs_breakdown:
            subqueries = parsed_content.get("subqueries", [])
            if len(subqueries) > 3:
                subqueries = subqueries[:3]

            if not subqueries:
                subqueries = [user_input]
        else:
            subqueries = [user_input]

        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": explanation,
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
                    },
                )
            ],
        }
    except Exception as e:
        error_msg = f"Error parsing subqueries: {e!s}"
        default_subqueries = [user_input]

        return {
            "user_query": user_input,
            "subquery_index": -1,
            "subqueries": default_subqueries,
            "query_result": query_result_object,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }
