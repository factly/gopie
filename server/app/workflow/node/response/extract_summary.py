from app.models.message import IntermediateStep
from app.utils.summary_extraction import create_result_summary
from app.workflow.graph.types import State


async def extract_summary(state: State) -> dict:
    """
    Extract a summary for a specific subquery, especially for large results.

    Args:
        state: The current state object with query results and subquery_index

    Returns:
        Updated state with the summary added to the identified subquery
    """
    query_result = state.get("query_result", None)
    subquery_index = state.get("subquery_index", 0)

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

    if not subquery.contains_large_results or subquery.summary:
        return {
            "query_result": query_result,
            "messages": [
                IntermediateStep.from_json(
                    {
                        "message": subquery.summary
                        or "No summary needed for this result."
                    }
                )
            ],
        }

    result = subquery.query_result
    summary = create_result_summary(result)

    query_result.subqueries[subquery_index].summary = summary
    query_result.subqueries[subquery_index].query_result = None

    return {
        "query_result": query_result,
        "messages": [IntermediateStep.from_json(summary)],
    }
