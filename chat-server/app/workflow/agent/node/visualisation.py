from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.visualize_with_code_graph import (
    graph as visualize_with_code_graph,
)

from ..types import AgentState


@configure_node(
    role="intermediate",
    progress_message="Checking visualization needs...",
)
async def check_visualization(
    state: AgentState, config: RunnableConfig
) -> dict:
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

    llm = get_llm_for_node("check_visualization", config)
    response = await llm.ainvoke(
        {
            "input": prompt_messages,
            "chat_history": get_chat_history(config),
        }
    )

    parser = JsonOutputParser()
    parsed_response = parser.parse(str(response.content))
    needs_visualization = parsed_response.get("wants_visualization", False)
    return {"needs_visualization": needs_visualization}


async def call_visualization_agent(
    state: AgentState, config: RunnableConfig
) -> AgentState:
    input_state = {
        "user_query": state.get("user_query", ""),
        "datasets": state.get("datasets", []),
    }

    _ = await visualize_with_code_graph.ainvoke(input_state, config=config)
