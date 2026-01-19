from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig

from app.core.log import custom_logger as logger
from app.models.message import ErrorMessage, IntermediateStep
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.multi_dataset_graph.types import State
from app.workflow.graph.sql_planner_graph.graph import sql_planning_agent
from app.workflow.graph.sql_planner_graph.types import (
    InputState as SqlPlannerInputState,
)


@configure_node(
    role="intermediate",
    progress_message="Planning query...",
)
async def sql_agent(state: State, config: RunnableConfig) -> dict:
    identified_datasets = state.get("identified_datasets", [])
    query_index = state.get("subquery_index", 0)
    user_query = state.get("subqueries")[query_index] if state.get("subqueries") else "No input"
    query_result = state.get("query_result", {})
    datasets_info = state.get("datasets_info", {})
    prev_sql_queries = state.get("prev_sql_queries", [])
    validation_result = state.get("validation_result", None)

    try:
        if not identified_datasets:
            raise Exception("No dataset selected for query planning")

        retry_count = query_result.subqueries[query_index].retry_count

        if not datasets_info:
            raise Exception("Could not get preview information for any of the selected datasets")

        chain_input: SqlPlannerInputState = {
            "user_query": user_query,
            "multi_datasets_info": datasets_info,
            "single_dataset_info": None,
            "retry_count": retry_count,
            "prev_sql_queries": prev_sql_queries,
            "validation_result": validation_result,
        }

        agent_output = await sql_planning_agent.ainvoke(chain_input, config=config)

        sql_queries = agent_output.get("sql_queries", [])
        non_sql_response = agent_output.get("non_sql_response", "")
        limitations = agent_output.get("limitations", [])
        tables_used = agent_output.get("tables_used", [])

        query_result.subqueries[query_index].sql_queries = sql_queries
        query_result.subqueries[query_index].non_sql_response = non_sql_response
        query_result.subqueries[query_index].tables_used = tables_used

        if non_sql_response:
            query_result.set_node_message(
                "plan_query",
                {
                    "query_strategy": "non_sql_response",
                    "non_sql_response": non_sql_response,
                    "limitations": limitations,
                },
            )
        elif sql_queries:
            query_result.set_node_message(
                "plan_query",
                {
                    "query_strategy": (
                        "single_query" if len(sql_queries) == 1 else "multiple_queries"
                    ),
                    "tables_used": list(set(tables_used)),
                    "query_count": len(sql_queries),
                    "limitations": limitations,
                },
            )
        else:
            raise Exception(
                "Invalid response: must contain either 'sql_queries' or 'non_sql_response'"
            )

        return {
            "query_result": query_result,
            "messages": [
                IntermediateStep(
                    content="Succesfully Completed query planning step in multidataset workflow."
                )
            ],
        }

    except Exception as e:
        error_msg = f"Unexpected error in query planning: {e!s}"
        query_result.add_error_message(error_msg, "Error in query planning")

        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "Error in query planning",
            },
        )

        logger.exception(error_msg)

        return {
            "query_result": query_result,
            "messages": [ErrorMessage(content=error_msg)],
        }
