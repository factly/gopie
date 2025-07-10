from app.models.query import QueryResult


def format_multi_query_result(query_result: QueryResult) -> str:
    user_query = query_result.original_user_query

    input_parts = [
        f"USER QUERY: {user_query}",
        f"EXECUTION TIME: {query_result.execution_time:.2f}s",
    ]

    if query_result.has_subqueries():
        input_parts.append(
            f"SUBQUERIES PROCESSED: {len(query_result.subqueries)}"
        )

        for i, subquery in enumerate(query_result.subqueries, 1):
            subquery_section = [f"\n--- SUBQUERY {i} ---"]
            subquery_section.append(f"Query: {subquery.query_text}")

            if subquery.query_type:
                subquery_section.append(f"Type: {subquery.query_type}")

            if subquery.tables_used:
                subquery_section.append(f"Tables: {subquery.tables_used}")

            if subquery.sql_queries:
                subquery_section.append(
                    f"SQL Queries Executed: {len(subquery.sql_queries)}"
                )
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
                subquery_section.append(
                    f"Tool Result: {subquery.tool_used_result}"
                )

            if subquery.error_message:
                subquery_section.append("Errors encountered:")
                for error in subquery.error_message:
                    for error_type, error_msg in error.items():
                        subquery_section.append(f"- {error_type}: {error_msg}")

            if subquery.confidence_score != 5:
                subquery_section.append(
                    f"Confidence: {subquery.confidence_score}/10"
                )

            if subquery.node_messages:
                subquery_section.append("Additional Context:")
                for node, message in subquery.node_messages.items():
                    subquery_section.append(f"- {node}: {message}")

            input_parts.extend(subquery_section)
    else:
        input_parts.append("No subqueries were processed")

    input_str = "\n".join(input_parts)

    return input_str
