from langchain_core.runnables import RunnableConfig

from app.core.log import custom_logger as logger
from app.services.qdrant.get_schema import get_schema_from_qdrant
from app.workflow.graph.nl_to_sql_graph.types import SqlQuery, State
from app.workflow.graph.sql_planner_graph.graph import sql_planning_agent
from app.workflow.graph.sql_planner_graph.types import (
    InputState as SqlPlannerInputState,
)


async def sql_agent(state: State, config: RunnableConfig) -> dict:
    """
    Generate SQL queries using the sql_planning_agent.

    Handles both single and multi-dataset cases:
    - Single dataset: fetches schema from Qdrant using dataset_id and passes as single_dataset_info
    - Multi-dataset: uses semantic_search_results from prior semantic_search node as multi_datasets_info
    """
    user_query = state.get("user_query", "") or ""
    dataset_ids = state.get("dataset_ids") or []
    semantic_search_results = state.get("semantic_search_results")

    try:
        single_dataset_info = None
        multi_datasets_info = None

        if semantic_search_results:
            multi_datasets_info = {
                "schemas": semantic_search_results,
                "column_assumptions": None,
                "correct_column_requirements": None,
            }
        elif dataset_ids:
            dataset_id = dataset_ids[0]
            schema = await get_schema_from_qdrant(dataset_id=dataset_id)
            if schema is None:
                return {"sql_queries": [], "message": None}

            single_dataset_info = {
                "dataset_schema": schema,
                "sample_data_csv": "",
                "column_assumptions": None,
                "correct_column_requirements": None,
            }
        else:
            return {"sql_queries": [], "message": None}

        sql_agent_input: SqlPlannerInputState = {
            "user_query": user_query,
            "single_dataset_info": single_dataset_info,
            "multi_datasets_info": multi_datasets_info,
            "retry_count": 0,
            "validation_result": None,
            "prev_sql_queries": None,
        }

        agent_output = await sql_planning_agent.ainvoke(sql_agent_input, config=config)

        sql_queries_info = agent_output.get("sql_queries", [])

        sql_queries: list[SqlQuery] = []
        if sql_queries_info:
            for sql_query_info in sql_queries_info:
                sql_queries.append(
                    SqlQuery(
                        query=sql_query_info.sql_query,
                        description=sql_query_info.explanation,
                    )
                )

        message = agent_output.get("non_sql_response", None)
        return {"sql_queries": sql_queries, "message": message}

    except Exception as e:
        logger.error(f"Error in sql_agent: {e}")
        return {"sql_queries": [], "message": None}
