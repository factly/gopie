from app.core.log import logger
from app.services.gopie.sql_executor import execute_sql
from app.workflow.graph.visualize_data_graph.types import Dataset, State


async def pre_process_visualization_data(state: State) -> dict:
    datasets = state["datasets"] or []
    relevant_sql_queries = state["relevant_sql_queries"] or []

    try:
        for sql_query in relevant_sql_queries:
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
        "datasets": datasets,
        "feedback_count": 0,
    }
