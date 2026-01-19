from app.workflow.graph.single_dataset_graph.types import State


def route_after_sql_generation(state: State) -> str:
    query_result = state.get("query_result", [])
    single_dataset_res = query_result.single_dataset_query_result

    sql_queries = (
        [sq.sql_query for sq in single_dataset_res.sql_queries if sq.sql_query]
        if single_dataset_res and single_dataset_res.sql_queries
        else []
    )

    if not sql_queries:
        return "no_sql_queries"

    return "execute_sql"
