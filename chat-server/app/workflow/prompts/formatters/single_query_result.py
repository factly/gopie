from app.workflow.graph.single_dataset_graph.types import (
    SingleDatasetQueryResult,
)


def format_single_query_result(
    query_result: SingleDatasetQueryResult, **kwargs
) -> str:
    if not query_result:
        return "No query result found"

    user_query = query_result.get("user_query", "")
    dataset_name = query_result.get("dataset_name", "Error occurred")
    user_friendly_dataset_name = query_result.get(
        "user_friendly_dataset_name", dataset_name
    )
    sql_results = query_result.get("sql_results")
    response_for_non_sql = query_result.get("response_for_non_sql", "")
    error = query_result.get("error")

    input_parts = [
        f"USER QUERY: {user_query}",
        f"DATASET: {user_friendly_dataset_name} (table: {dataset_name})",
    ]

    if error:
        input_parts.append(f"\nERROR: {error}")
        formatted_input = "\n".join(input_parts)
        return formatted_input

    if response_for_non_sql:
        input_parts.append(f"\nNON-SQL RESPONSE:\n{response_for_non_sql}")
        formatted_input = "\n".join(input_parts)
        return formatted_input

    if sql_results is not None:
        successful_results = [r for r in sql_results if r.get("success", True)]
        failed_results = [r for r in sql_results if not r.get("success", True)]

        if successful_results:
            input_parts.append("\n--- QUERY RESULTS ---")
            for i, result in enumerate(successful_results, 1):
                if result.get("result"):
                    explanation = result.get("explanation", "")
                    sql_query = result.get("sql_query", "")
                    data_preview = result["result"]
                    large_result = result.get("large_result")

                    input_parts.append(f"\nSQL Query {i}:")
                    if explanation:
                        input_parts.append(f"Purpose: {explanation}")
                    if sql_query:
                        input_parts.append(f"SQL: {sql_query}")

                    if large_result:
                        input_parts.append(f"⚠️  Large Result: {large_result}")
                        input_parts.append(f"Data (truncated): {data_preview}")
                    else:
                        input_parts.append(f"Data: {data_preview}")

        if failed_results:
            input_parts.append("\n--- FAILED QUERIES ---")
            input_parts.append("Some SQL queries were not successful:")
            for i, result in enumerate(failed_results, 1):
                sql_query = result.get("sql_query", "")
                error = result.get("error", "Unknown error")
                explanation = result.get("explanation", "")

                input_parts.append(f"\nFailed Query {i}:")
                if explanation:
                    input_parts.append(f"Purpose: {explanation}")
                if sql_query:
                    input_parts.append(f"SQL: {sql_query}")
                input_parts.append(f"Error: {error}")

    formatted_input = "\n".join(input_parts)
    return formatted_input
