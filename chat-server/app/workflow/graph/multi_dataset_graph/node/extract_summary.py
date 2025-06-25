from app.models.message import IntermediateStep
from app.utils.graph_utils.summary_extraction import create_result_summary
from app.workflow.graph.multi_dataset_graph.types import State


async def extract_summary(state: State) -> dict:
    """
    Extract summaries for SQL query results in a specific subquery,
    especially for large results.

    Args:
        state: The current state object with query results and subquery_index

    Returns:
        Updated state with summaries added to the identified SQL queries
    """
    query_result = state.get("query_result", None)
    subquery_index = state.get("subquery_index", 0)

    if not query_result or not hasattr(query_result, "subqueries"):
        return {
            "messages": [
                IntermediateStep.from_json(
                    {"message": "No query result available."}
                )
            ],
            "query_result": query_result,
        }

    if not (0 <= subquery_index < len(query_result.subqueries)):
        return {
            "messages": [
                IntermediateStep.from_json(
                    {"message": f"Invalid subquery index: {subquery_index}."}
                )
            ],
            "query_result": query_result,
        }

    subquery = query_result.subqueries[subquery_index]

    summaries_created = False
    result_messages = []

    for i, sql_query_info in enumerate(subquery.sql_queries):
        no_large_results = not sql_query_info.contains_large_results
        has_summary = sql_query_info.summary

        if no_large_results or has_summary:
            continue

        result = sql_query_info.sql_query_result
        if result:
            summary = create_result_summary(result)
            sql_query_info.contains_large_results = False
            sql_query_info.summary = summary
            sql_query_info.sql_query_result = None
            summaries_created = True

            sq_idx = subquery_index + 1
            result_messages.append(
                f"Created summary for SQL query {i + 1} in subquery {sq_idx}"
            )

    if not summaries_created:
        message = "No summaries needed for this subquery."
    else:
        message = "; ".join(result_messages)

    return {
        "query_result": query_result,
        "messages": [IntermediateStep.from_json({"message": message})],
    }
