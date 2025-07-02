from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage


def create_response_prompt(input: str, **kwargs) -> list[BaseMessage]:
    system_message = SystemMessage(
        content="""You are a helpful data analyst. Provide clear, helpful
responses based on the available data. Be conversational and focus on insights.

GUIDELINES:
- Base your response ONLY on the data provided
- Do not add information that isn't present in the results
- Be conversational and engaging
- Focus on key insights and patterns in the data
- Explain findings in simple, understandable terms
- If there are failed queries, acknowledge any limitations in your analysis
- Structure your response clearly with the most important insights first"""
    )

    human_message = HumanMessage(content=input)

    return [system_message, human_message]


def format_response_input(query_result: dict, **kwargs) -> dict:
    if not query_result:
        return {"input": "No query result found"}

    user_query = query_result.get("user_query", "")
    dataset_name = query_result.get("dataset_name", "Error occurred")
    user_friendly_dataset_name = query_result.get(
        "user_friendly_dataset_name", dataset_name
    )
    sql_queries = query_result.get("sql_queries", [])
    response_for_non_sql = query_result.get("response_for_non_sql", "")

    input_parts = [
        f"USER QUERY: {user_query}",
        f"DATASET: {user_friendly_dataset_name} (table: {dataset_name})",
    ]

    if response_for_non_sql:
        input_parts.append(f"\nNON-SQL RESPONSE:\n{response_for_non_sql}")
        formatted_input = "\n".join(input_parts)
        return {"input": formatted_input}

    successful_results = [r for r in sql_queries if r.get("success", True)]
    failed_results = [r for r in sql_queries if not r.get("success", True)]

    if successful_results:
        input_parts.append("\n--- QUERY RESULTS ---")
        for i, result in enumerate(successful_results, 1):
            if result.get("result"):
                explanation = result.get("explanation", "")
                sql_query = result.get("sql_query", "")
                data_preview = result["result"]

                input_parts.append(f"\nQuery {i}:")
                if explanation:
                    input_parts.append(f"Purpose: {explanation}")
                if sql_query:
                    input_parts.append(f"SQL: {sql_query}")
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
    return {"input": formatted_input}
