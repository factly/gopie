from app.workflow.graph.single_dataset_graph.types import (
    SingleDatasetQueryResult,
)


def format_single_query_result(query_result: SingleDatasetQueryResult, **kwargs) -> str:
    if not query_result:
        return "No query result found"

    user_query = query_result.get("user_query", "")
    dataset_name = query_result.get("dataset_name", "Error occurred")
    user_friendly_dataset_name = query_result.get("user_friendly_dataset_name", dataset_name)
    sql_results = query_result.get("sql_results")
    response_for_non_sql = query_result.get("response_for_non_sql", "")
    error = query_result.get("error")

    input_str = f"""USER QUERY: {user_query}
DATASET: {user_friendly_dataset_name} (table: {dataset_name})"""

    if error:
        input_str += f"\n\nERROR: {error}"

    if response_for_non_sql:
        input_str += f"\n\nNON-SQL RESPONSE:\n{response_for_non_sql}"

    if sql_results is not None:
        successful_results = [r for r in sql_results if r.get("success", True)]
        failed_results = [r for r in sql_results if not r.get("success", True)]

        if successful_results:
            input_str += "\n\n=== QUERY RESULTS ==="
            for i, result in enumerate(successful_results, 1):
                if result.get("result"):
                    explanation = result.get("explanation", "")
                    sql_query = result.get("sql_query", "")
                    data_preview = result["result"]

                    input_str += f"\n\n--- SQL Query {i} ---"
                    if explanation:
                        input_str += f"\nPurpose: {explanation}"
                    if sql_query:
                        input_str += f"\nSQL: {sql_query}"
                    input_str += f"\nData: {data_preview}"

        if failed_results:
            input_str += "\n\n=== FAILED QUERIES ==="
            input_str += "\nSome SQL queries were not successful:"
            for i, result in enumerate(failed_results, 1):
                sql_query = result.get("sql_query", "")
                error = result.get("error", "Unknown error")
                explanation = result.get("explanation", "")

                input_str += f"\n\n--- Failed Query {i} ---"
                if explanation:
                    input_str += f"\nPurpose: {explanation}"
                if sql_query:
                    input_str += f"\nSQL: {sql_query}"
                input_str += f"\nError: {error}"

    return input_str
