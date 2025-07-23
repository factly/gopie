from app.models.query import QueryResult, SingleDatasetQueryResult


def format_query_result(query_result: QueryResult) -> str:
    """
    Format a comprehensive query result into a detailed, human-readable multi-line string.

    The output includes the original user query, execution time, and, if present, a formatted summary of a single dataset query result. If subqueries exist, each is detailed with its query text, type, tables used, executed SQL queries (including their explanations and results), tool results, error messages, confidence scores (if not default), and any additional context messages. If no subqueries are present, the output notes this explicitly.

    Parameters:
        query_result (QueryResult): The query result object to format.

    Returns:
        str: A structured string summarizing the query result, including subqueries and their details.
    """
    user_query = query_result.original_user_query

    input_parts = [
        f"USER QUERY: {user_query}",
        f"EXECUTION TIME: {query_result.execution_time:.2f}s",
    ]

    if query_result.single_dataset_query_result:
        input_parts.append("\n=== SINGLE DATASET QUERY RESULT ===")
        input_parts.append(
            format_single_dataset_query_result(query_result.single_dataset_query_result)
        )

    if query_result.has_subqueries():
        input_parts.append(f"SUBQUERIES PROCESSED: {len(query_result.subqueries)}")

        for i, subquery in enumerate(query_result.subqueries, 1):
            subquery_section = [f"\n--- SUBQUERY {i} ---"]
            subquery_section.append(f"Query: {subquery.query_text}")

            if subquery.query_type:
                subquery_section.append(f"Type: {subquery.query_type}")

            if subquery.tables_used:
                subquery_section.append(f"Tables: {subquery.tables_used}")

            if subquery.sql_queries:
                subquery_section.append(f"SQL Queries Executed: {len(subquery.sql_queries)}")
                for j, sql_info in enumerate(subquery.sql_queries, 1):
                    sql_section = [f"\nSQL Query {j}:"]
                    sql_section.append(f"Query: {sql_info.sql_query}")
                    sql_section.append(f"Explanation: {sql_info.explanation}")

                    sql_result = sql_info.sql_query_result

                    if sql_result is not None:
                        sql_section.append(f"Result: {sql_result}")
                    else:
                        sql_section.append("Result: No data returned")

                    subquery_section.extend(sql_section)

            if subquery.tool_used_result is not None:
                subquery_section.append(f"Tool Result: {subquery.tool_used_result}")

            if subquery.error_message:
                subquery_section.append("Errors encountered:")
                for error in subquery.error_message:
                    for error_type, error_msg in error.items():
                        subquery_section.append(f"- {error_type}: {error_msg}")

            if subquery.confidence_score != 5:
                subquery_section.append(f"Confidence: {subquery.confidence_score}/10")

            if subquery.node_messages:
                subquery_section.append("Additional Context:")
                for node, message in subquery.node_messages.items():
                    subquery_section.append(f"- {node}: {message}")

            input_parts.extend(subquery_section)
    else:
        input_parts.append("No subqueries were processed")

    input_str = "\n".join(input_parts)

    return input_str


def format_single_dataset_query_result(single_result: SingleDatasetQueryResult) -> str:
    """
    Format the results of a single dataset query into a structured, human-readable string.

    Includes dataset names, error messages, non-SQL responses, and details for both successful and failed SQL queries, such as explanations, SQL statements, data previews, and error messages.

    Returns:
        str: A formatted summary of the single dataset query result.
    """
    user_friendly_dataset_name = single_result.user_friendly_dataset_name or "Unknown"
    dataset_name = single_result.dataset_name or "Unknown"
    sql_results = single_result.sql_results
    response_for_non_sql = single_result.response_for_non_sql
    error = single_result.error

    input_str = f"DATASET: {user_friendly_dataset_name} (table: {dataset_name})"

    if error:
        input_str += f"\n\nERROR: {error}"

    if response_for_non_sql:
        input_str += f"\n\nNON-SQL RESPONSE:\n{response_for_non_sql}"

    if sql_results is not None:
        successful_results = [r for r in sql_results if r.success]
        failed_results = [r for r in sql_results if not r.success]

        if successful_results:
            input_str += "\n\n=== QUERY RESULTS ==="
            for i, result in enumerate(successful_results, 1):
                if result.sql_query_result:
                    explanation = result.explanation
                    sql_query = result.sql_query
                    data_preview = result.sql_query_result

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
                sql_query = result.sql_query
                error = result.error
                explanation = result.explanation

                input_str += f"\n\n--- Failed Query {i} ---"
                if explanation:
                    input_str += f"\nPurpose: {explanation}"
                if sql_query:
                    input_str += f"\nSQL: {sql_query}"
                input_str += f"\nError: {error}"

    return input_str
