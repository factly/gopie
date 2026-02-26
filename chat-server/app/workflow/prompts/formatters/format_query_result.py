from app.models.query import (
    AnalyzeQueryResult,
    QueryResult,
    SingleDatasetQueryResult,
    SqlQueryInfo,
    SubQueryInfo,
)
from app.models.schema import DatasetSchema


def format_sql_query_info(sql_info: SqlQueryInfo, query_number: int) -> str:
    """
    Format a single SQL query information object into a readable string.

    Args:
        sql_info: The SQL query information to format
        query_number: The number/index of this query

    Returns:
        str: Formatted SQL query information
    """
    sql_section = [f"\nSQL Query {query_number}:"]
    sql_section.append(f"Query: {sql_info.sql_query}")
    sql_section.append(f"Explanation: {sql_info.explanation}")

    if sql_info.sql_query_result is not None:
        sql_section.append(f"Result: {sql_info.sql_query_result}")
    else:
        sql_section.append("Result: No data returned")

    if not sql_info.success and sql_info.error:
        sql_section.append(f"Error: {sql_info.error}")

    return "\n".join(sql_section)


def format_successful_sql_results(sql_results: list[SqlQueryInfo]) -> str:
    """
    Format successful SQL query results for single dataset queries.

    Args:
        sql_results: List of successful SQL query results

    Returns:
        str: Formatted successful results section
    """
    sections = ["\n\n=== QUERY RESULTS ==="]

    for i, result in enumerate(sql_results, 1):
        if result.sql_query_result:
            sections.append(f"\n\n--- SQL Query {i} ---")
            if result.explanation:
                sections.append(f"\nPurpose: {result.explanation}")
            if result.sql_query:
                sections.append(f"\nSQL: {result.sql_query}")
            sections.append(f"\nData: {result.sql_query_result}")

    return "".join(sections)


def format_failed_sql_results(sql_results: list[SqlQueryInfo]) -> str:
    """
    Format failed SQL query results for single dataset queries.

    Args:
        sql_results: List of failed SQL query results

    Returns:
        str: Formatted failed results section
    """
    sections = ["\n\n=== FAILED QUERIES ==="]
    sections.append("\nSome SQL queries were not successful:")

    for i, result in enumerate(sql_results, 1):
        sections.append(f"\n\n--- Failed Query {i} ---")
        if result.explanation:
            sections.append(f"\nPurpose: {result.explanation}")
        if result.sql_query:
            sections.append(f"\nSQL: {result.sql_query}")
        sections.append(f"\nError: {result.error}")

    return "".join(sections)


def format_analyze_query_result(analyze_result: AnalyzeQueryResult) -> str:
    """
    Format the analyze query result into a readable string.

    Args:
        analyze_result: The analyze query result to format

    Returns:
        str: Formatted analyze query result
    """
    sections = []

    if analyze_result.query_type:
        sections.append(f"Query Type: {analyze_result.query_type}")

    if analyze_result.response:
        sections.append(f"Analysis Response: {analyze_result.response}")

    if analyze_result.tool_used_result:
        sections.append("Tool Results:")
        for tool_result in analyze_result.tool_used_result:
            tool_name = tool_result.get("name", "Unknown Tool")
            tool_content = tool_result.get("content", "No content")
            tool_call_id = tool_result.get("tool_call_id", "Unknown ID")
            sections.append(f"  - {tool_name} (ID: {tool_call_id}): {tool_content}")

    if analyze_result.confidence_score != 5:
        sections.append(f"Confidence Score: {analyze_result.confidence_score}/10")

    return "\n".join(sections) if sections else "No analysis result available"


def format_subquery_info(subquery: SubQueryInfo, subquery_number: int) -> list[str]:
    """
    Format a single subquery information object into readable sections.

    Args:
        subquery: The subquery information to format
        subquery_number: The number/index of this subquery

    Returns:
        list[str]: List of formatted sections for the subquery
    """
    subquery_section = [f"\n--- SUBQUERY {subquery_number} ---"]
    subquery_section.append(f"Query: {subquery.query_text}")

    if subquery.tables_used:
        subquery_section.append(f"Tables: {subquery.tables_used}")

    if subquery.sql_queries:
        subquery_section.append(f"SQL Queries Executed: {len(subquery.sql_queries)}")
        for j, sql_info in enumerate(subquery.sql_queries, 1):
            sql_formatted = format_sql_query_info(sql_info, j)
            subquery_section.append(sql_formatted)

    if subquery.non_sql_response:
        subquery_section.append(f"Non SQL Response: {subquery.non_sql_response}")

    if subquery.error_message:
        subquery_section.append("Errors encountered:")
        for error in subquery.error_message:
            for error_type, error_msg in error.items():
                subquery_section.append(f"- {error_type}: {error_msg}")

    if subquery.node_messages:
        subquery_section.append("Additional Context:")
        for node, message in subquery.node_messages.items():
            subquery_section.append(f"- {node}: {message}")

    return subquery_section


def format_dataset_schemas(schemas: list[DatasetSchema]) -> str:
    """
    Format a list of dataset schemas into a readable string for the result generation prompt.

    Args:
        schemas: List of DatasetSchema objects

    Returns:
        str: Formatted dataset schemas section
    """
    if not schemas:
        return ""

    sections = ["\n=== DATASET SCHEMAS ==="]
    for schema in schemas:
        sections.append(
            schema.format_for_prompt(columns_fields_to_exclude=["sample_values", "avg", "std"])
        )
    return "\n".join(sections)


def format_query_result(
    query_result: QueryResult,
    *,
    dataset_schemas: list[DatasetSchema] | None = None,
) -> str:
    """
    Format a comprehensive query result into a detailed, human-readable multi-line string.

    The output includes the original user query, execution time, analyze query result, and, if present, a formatted summary of a single dataset query result. If subqueries exist, they are categorized into two sections:
    1. Executed subqueries: Detailed with their query text, tables used, executed SQL queries (including their explanations and results), error messages, and any additional context messages.
    2. Pending subqueries: Listed with their query text and a note that they will be executed and processed further.

    Only includes subqueries that have been executed (have SQL queries with results, have a non_sql_response, or have error messages) in the main results section.

    Parameters:
        query_result (QueryResult): The query result object to format.

    Returns:
        str: A structured string summarizing the query result, including executed subqueries and pending subqueries.
    """
    user_query = query_result.original_user_query

    input_parts = [
        f"USER QUERY: {user_query}",
        f"EXECUTION TIME: {query_result.execution_time:.2f}s",
    ]

    if dataset_schemas:
        input_parts.append(format_dataset_schemas(dataset_schemas))

    if query_result.analyze_query_result:
        input_parts.append("\n=== QUERY ANALYSIS ===")
        input_parts.append(format_analyze_query_result(query_result.analyze_query_result))

    if query_result.single_dataset_query_result:
        input_parts.append("\n=== SINGLE DATASET QUERY RESULT ===")
        input_parts.append(
            format_single_dataset_query_result(query_result.single_dataset_query_result)
        )

    if query_result.has_subqueries():
        executed_subqueries = [
            subquery for subquery in query_result.subqueries if _is_subquery_executed(subquery)
        ]
        pending_subqueries = [
            subquery for subquery in query_result.subqueries if not _is_subquery_executed(subquery)
        ]

        if executed_subqueries:
            input_parts.append(f"SUBQUERIES PROCESSED: {len(executed_subqueries)}")

            for i, subquery in enumerate(executed_subqueries, 1):
                subquery_sections = format_subquery_info(subquery, i)
                input_parts.extend(subquery_sections)
        else:
            input_parts.append("No subqueries have been executed yet")

        if pending_subqueries:
            input_parts.append(
                f"\nPENDING SUBQUERIES: {len(pending_subqueries)} remaining to be processed"
            )
            for i, subquery in enumerate(pending_subqueries, 1):
                input_parts.append(f"\n--- PENDING SUBQUERY {i} ---")
                input_parts.append(f"Query: {subquery.query_text}")
                input_parts.append(
                    "Status: Will be processed further so don't validate this subquery"
                )
    else:
        has_single_dataset_sql = (
            query_result.single_dataset_query_result
            and query_result.single_dataset_query_result.sql_queries
            and len(query_result.single_dataset_query_result.sql_queries) > 0
        )
        if not has_single_dataset_sql:
            input_parts.append("No SQL queries were processed")

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
    sql_queries = single_result.sql_queries
    non_sql_response = single_result.non_sql_response
    error = single_result.error

    input_str = f"DATASET: {user_friendly_dataset_name} (table: {dataset_name})"

    if error:
        input_str += f"\n\nERROR: {error}"

    if non_sql_response:
        input_str += f"\n\nNON-SQL INFORMATION:\n{non_sql_response}"

    if sql_queries is not None:
        successful_results = [r for r in sql_queries if r.success]
        failed_results = [r for r in sql_queries if not r.success]

        if successful_results:
            input_str += format_successful_sql_results(successful_results)

        if failed_results:
            input_str += format_failed_sql_results(failed_results)

    return input_str


def _is_subquery_executed(subquery: SubQueryInfo) -> bool:
    """
    Check if a subquery has been executed.
    Args:
        subquery: The subquery to check

    Returns:
        bool: True if the subquery has been executed, False otherwise
    """
    return (
        bool(subquery.sql_queries)
        or bool(subquery.non_sql_response)
        or bool(subquery.error_message)
    )
