from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.single_dataset_graph.types import State


@configure_node(
    role="ai",
    progress_message="",
)
async def response(state: State, config: RunnableConfig) -> dict:
    query_result = state.get("query_result", {})

    if not query_result:
        return {"messages": [AIMessage(content="No query result found")]}

    user_query = query_result.get("user_query", "")
    dataset_name = query_result.get("dataset_name", "Error occurred")
    sql_queries = query_result.get("sql_queries", [])

    successful_results = [r for r in sql_queries if r.get("success", True)]

    data_context = ""
    if successful_results:
        data_context = "Data from your query:\n"
        for i, result in enumerate(successful_results, 1):
            if result.get("result"):
                data_preview = result["result"]
                data_context += f"Query {i}: {data_preview}\n"

    failed_results = [r for r in sql_queries if not r.get("success", True)]

    if failed_results:
        data_context += "\n\nSome SQL queries were not successful.\n"
        for result in failed_results:
            data_context += f"{result}\n\n"

    prompt_messages = get_prompt(
        "response",
        user_query=user_query,
        dataset_name=dataset_name,
        data_context=data_context,
    )

    llm = get_llm_for_node("response", config)
    response_result = await llm.ainvoke(
        {"input": prompt_messages, "chat_history": get_chat_history(config)}
    )

    return {"messages": [AIMessage(content=str(response_result.content))]}
