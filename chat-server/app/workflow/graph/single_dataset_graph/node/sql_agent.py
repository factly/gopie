from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.core.log import custom_logger as logger
from app.workflow.graph.single_dataset_graph.types import State
from app.workflow.graph.sql_planner_graph.graph import sql_planning_agent
from app.workflow.graph.sql_planner_graph.types import (
    InputState as SqlPlannerInputState,
)


async def sql_agent(state: State, config: RunnableConfig) -> dict:
    user_query = state.get("user_query", "") or ""
    dataset_info = state.get("dataset_info", None)
    prev_sql_queries = state.get("prev_sql_queries", [])
    validation_result = state.get("validation_result", None)
    query_result = state.get("query_result")

    single_dataset_result = query_result.single_dataset_query_result

    if not query_result or not single_dataset_result:
        raise ValueError("query_result is not properly initialized")

    try:
        sql_agent_input: SqlPlannerInputState = {
            "user_query": user_query,
            "single_dataset_info": dataset_info,
            "multi_datasets_info": None,
            "retry_count": single_dataset_result.retry_count,
            "validation_result": validation_result,
            "prev_sql_queries": prev_sql_queries,
        }

        agent_output = await sql_planning_agent.ainvoke(sql_agent_input, config=config)

        single_dataset_result.sql_queries = agent_output.get("sql_queries")
        single_dataset_result.non_sql_response = agent_output.get("non_sql_response", "")

        # Get updated dataset info from planner (may have updated column requirements from matching)
        updated_dataset_info = agent_output.get("single_dataset_info")

        return {
            "messages": [
                AIMessage(
                    content=(
                        "SQL queries generated."
                        if single_dataset_result.sql_queries
                        else "No SQL queries generated."
                    )
                )
            ],
            "query_result": query_result,
            "dataset_info": updated_dataset_info or dataset_info,
        }

    except Exception as e:
        error_message = f"Error in SQL planner agent: {str(e)}"
        single_dataset_result.error = error_message

        logger.exception(error_message)

        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "Error planning SQL queries",
            },
        )

        return {
            "messages": [
                AIMessage(
                    content=(
                        f"I'm sorry, but I encountered an error while "
                        f"planning your query: {error_message}"
                    )
                )
            ],
            "query_result": query_result,
        }
