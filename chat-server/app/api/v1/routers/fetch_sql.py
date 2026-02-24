from fastapi import APIRouter, HTTPException, status

from app.core.log import custom_logger as logger
from app.models.router import FetchSqlRequest, FetchSqlResponse
from app.workflow.graph.nl_to_sql_graph.graph import nl_to_sql_graph

fetch_sql_router = APIRouter()


@fetch_sql_router.post("/fetch-sql", response_model=FetchSqlResponse)
async def fetch_sql(payload: FetchSqlRequest):
    """
    Generate SQL queries from a natural language description.

    - Single dataset: provide `dataset_ids` with one ID
    - Multi-dataset: provide `dataset_ids` with multiple IDs and/or `project_ids`

    Returns a list of generated SQL queries with their explanations.
    """
    try:
        dataset_ids = [did for did in (payload.dataset_ids or []) if did]
        project_ids = [pid for pid in (payload.project_ids or []) if pid]

        result = await nl_to_sql_graph.ainvoke(
            {
                "user_query": payload.description,
                "dataset_ids": dataset_ids or None,
                "project_ids": project_ids or None,
            }
        )

        return FetchSqlResponse(
            sql_queries=result.get("sql_queries", []),
            message=result.get("message"),
        )
    except Exception as e:
        logger.error(f"Error in fetch_sql: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate SQL queries, please try again.",
        ) from e
