from typing import Any
from venv import logger

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)


async def supervisor(state: Any, config: RunnableConfig) -> dict:
    """
    Supervisor agent that routes between visualization and regular response
    based on the user's intent and query results.
    """
    query_result = state.get("query_result", {})
    user_query = query_result.get("user_query", "")
    sql_queries = query_result.get("sql_queries", [])

    successful_results = [r for r in sql_queries if r.get("success", True)]
    has_data = bool(
        successful_results and any(r.get("result") for r in successful_results)
    )

    if not has_data:
        return {"next_action": "response"}

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content="""
                You are a routing supervisor for a data analysis system.
                Analyze the user's question to determine if they want data
                visualization (charts, graphs, plots) or just a text
                response.
                Consider visualization keywords like: plot, chart, graph,
                visualize, show, display, trend, comparison, distribution,
                etc.
                """
            ),
            HumanMessage(
                content="""
                User question: {question}
                Available data: {data_summary}
                Respond with JSON:
                {{
                    "wants_visualization": true/false,
                    "reasoning": "explanation of the decision"
                }}
                """
            ),
        ]
    )

    llm = get_llm_for_node("supervisor", config)
    response = await llm.ainvoke(
        {
            "input": prompt.format(
                question=user_query,
                data_summary=successful_results,
            ),
            "chat_history": get_chat_history(config),
        }
    )

    try:
        parser = JsonOutputParser()
        parsed_response = parser.parse(str(response.content))
        wants_visualization = parsed_response.get("wants_visualization", False)

        if wants_visualization:
            all_data = []
            for result in successful_results:
                if result.get("result"):
                    all_data.extend(result["result"])

            return {
                "next_action": "visualizer_agent",
                "visualization_data": all_data,
            }
        else:
            return {"next_action": "response"}

    except Exception as e:
        logger.error(f"Error parsing supervisor response: {e}")
        return {"next_action": "response"}


def route_supervisor(state: Any) -> str:
    return state.get("next_action", "response")
