from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.single_dataset_graph.types import State


@configure_node(
    role="intermediate",
    progress_message="Checking visualization needs...",
)
async def check_visualization(state: State, config: RunnableConfig) -> dict:
    user_query = state.get("user_query", "")

    raw_sql_queries_data = []
    query_result = state.get("query_result") or {}
    sql_queries = query_result.get("sql_queries", [])

    for result in sql_queries:
        if result.get("result") and result.get("success", True):
            raw_sql_queries_data.extend(result["result"])

    if not raw_sql_queries_data:
        return {
            "raw_sql_queries_data": raw_sql_queries_data,
            "wants_visualization": False,
            "reasoning": "",
        }

    prompt_messages = get_prompt(
        "check_visualization",
        user_query=user_query,
    )

    llm = get_llm_for_node("supervisor", config)
    response = await llm.ainvoke(
        {
            "input": prompt_messages,
            "chat_history": get_chat_history(config),
        }
    )

    try:
        parser = JsonOutputParser()
        parsed_response = parser.parse(str(response.content))
        wants_visualization = parsed_response.get("wants_visualization", False)

        return {
            "raw_sql_queries_data": raw_sql_queries_data,
            "wants_visualization": wants_visualization,
            "reasoning": parsed_response.get("reasoning", ""),
        }
    except Exception as e:
        logger.error(f"Error parsing check_visualization response: {e}")
        return {
            "raw_sql_queries_data": raw_sql_queries_data,
            "wants_visualization": False,
            "reasoning": "",
        }


def route_next_node(state: State, config: RunnableConfig) -> str:
    wants_visualization = state.get("wants_visualization", False)
    if wants_visualization:
        return "handoff_to_visualizer_agent"
    else:
        return "response"
