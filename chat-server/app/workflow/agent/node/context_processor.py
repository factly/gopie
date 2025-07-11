from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.services.gopie.sql_executor import execute_sql
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_model_provider,
)
from app.workflow.events.event_utils import configure_node

from ..types import AgentState, Dataset


@configure_node(
    role="intermediate",
    progress_message="Processing chat context...",
)
async def process_context(state: AgentState, config: RunnableConfig) -> dict:
    user_input = state.get("initial_user_query", "")
    chat_history = get_chat_history(config)
    if not chat_history:
        return {"user_query": user_input}

    prompt_messages = get_prompt(
        "process_context",
        current_query=user_input,
        chat_history=chat_history,
    )

    llm = get_model_provider(config).get_llm_for_node("process_context")
    response = await llm.ainvoke(prompt_messages)

    try:
        parser = JsonOutputParser()
        parsed_response = parser.parse(str(response.content))

        enhanced_query = parsed_response.get("enhanced_query", user_input)
        context_summary = parsed_response.get("context_summary", "")
        is_follow_up = parsed_response.get("is_follow_up", False)
        need_semantic_search = parsed_response.get("need_semantic_search", True)
        required_dataset_ids = parsed_response.get("required_dataset_ids", [])
        visualization_data = parsed_response.get("visualization_data", [])
        previous_sql_queries = parsed_response.get("previous_sql_queries", [])

        if context_summary and context_summary.strip():
            final_query = f"""
The original user query and the previous conversation history were processed
and the following context summary was added to the query:

{is_follow_up and "This is a follow-up question to a previous query." or ""}

User Query: {enhanced_query}

Context Summary: {context_summary}
"""
        else:
            final_query = enhanced_query

        datasets = []
        if visualization_data:
            for viz_data in visualization_data:
                if isinstance(viz_data, dict) and "data" in viz_data and "description" in viz_data:
                    dataset = Dataset(
                        data=viz_data["data"],
                        description=viz_data["description"],
                        csv_path=viz_data.get("csv_path"),
                    )
                    datasets.append(dataset)

        elif previous_sql_queries:
            try:
                for sql_query in previous_sql_queries:
                    query_snippet = sql_query[:100]
                    logger.debug(f"Executing SQL query for context: {query_snippet}...")
                    sql_result = await execute_sql(query=sql_query)

                    if sql_result:
                        data = [list(d.values()) for d in sql_result]
                        headers = list(sql_result[0].keys())
                        data = [headers] + data

                        dataset = Dataset(
                            data=data,
                            description=f"Query: {sql_query}",
                        )
                        datasets.append(dataset)
                    else:
                        logger.error(f"SQL execution failed: {sql_result}")

            except Exception as sql_error:
                logger.error(f"Error executing SQL queries: {sql_error!s}")

        return {
            "user_query": final_query,
            "need_semantic_search": need_semantic_search,
            "required_dataset_ids": required_dataset_ids,
            "datasets": datasets,
            "previous_sql_queries": previous_sql_queries,
        }

    except Exception as e:
        logger.error(f"Error processing context: {e!s}")
        return {"user_query": user_input}
