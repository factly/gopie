from langchain_core.messages import HumanMessage, SystemMessage

from app.models.query import QueryResult


def create_generate_result_prompt(input: str) -> list:
    system_content = """
You are generating the final response to a user query based on the query execution results.
This is the LAST step in the workflow.

RESPONSE INSTRUCTIONS:
1. Analyze the query result to determine the appropriate response type:
   - If there's data/results: Provide a data-focused analysis response
   - If there are no results: Provide a helpful explanation and suggestions
   - If it's a conversational query: Provide a direct conversational response

2. GENERAL RESPONSE GUIDELINES:
   - Answer the query directly and confidently based on all available information
   - Do not mention how you processed the information or your sources
   - Use a friendly, professional tone as if speaking directly to the user
   - Seamlessly integrate all relevant information from the available context
   - Use bullet points or numbered lists when presenting multiple pieces of information
   - Highlight the most important or directly relevant information first
   - NEVER fabricate data or make assumptions beyond what's provided in the context
   - If you encounter contradictory information, acknowledge it and provide the most reliable interpretation
   - Format your response for maximum readability
   - NEVER mention technical implementation details such as SQL queries, error codes, or processing steps

3. FOR DATA ANALYSIS QUERIES (when results contain data):
   - Begin with a direct, confident answer to the user's query
   - Focus on presenting insights and conclusions from the data, not the process
   - Structure your response in a logical flow:
     * Main findings and direct answer to the query
     * Supporting details and evidence from the data
     * Any additional insights or patterns discovered
     * Implications or actionable recommendations (if appropriate)

   - For numerical data:
     * Format properly with appropriate separators (e.g., 1,000,000)
     * Use currency symbols when relevant
     * Present percentages with appropriate precision

   - When presenting complex information:
     * Use bullet points or numbered lists for clarity
     * Group related information together
     * Use brief, descriptive subheadings if needed

   - If the data reveals patterns or trends:
     * Highlight these clearly
     * Explain their significance in context
     * Avoid technical jargon when explaining their meaning

4. FOR EMPTY/NO RESULTS QUERIES:
   - Acknowledge that no matching data was found for their specific query
   - Begin with a clear, direct statement that addresses what the user was looking for
   - Analyze the execution details to understand where the process encountered issues
   - Provide a helpful, constructive response that offers:
     * A brief explanation of why their query might not have returned results
     * 2-3 specific alternative approaches they could try
     * Suggestions for modifying their query to get better results
   - Be empathetic but confident, maintaining a helpful tone
   - Avoid technical jargon and error details - focus on what the user can do next
   - Personalize your response by referencing elements of their original query
   - Frame alternatives as positive suggestions rather than focusing on what didn't work
   - End with an encouraging note that invites them to try a modified approach

5. FOR CONVERSATIONAL QUERIES (tool-based or general queries):
   - Provide direct answers based on the available information
   - Integrate tool results naturally into the response
   - Maintain a conversational, helpful tone
   - Focus on answering the user's question comprehensively

6. IMPORTANT DON'Ts FOR ALL CASES:
   - Do NOT mention SQL queries, data processing steps, or technical implementation
   - Do NOT use phrases like "based on the data" or "according to the results" excessively
   - Do NOT include error messages or technical details in the response
   - Do NOT apologize excessively (especially for empty results)
   - Do NOT show technical error messages or processing details
   - Do NOT make up data that doesn't exist

7. TONE FOR ALL CASES:
   - Professional but conversational
   - Confident in presenting findings
   - Educational when explaining complex concepts
   - Neutral and objective when presenting facts
   - Empathetic when no results are found
"""

    human_content = f"""
    {input}
"""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]


def format_generate_result_input(
    user_query: str, query_result: QueryResult
) -> dict:
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

                    if sql_info.sql_query_result is not None:
                        if (
                            sql_info.contains_large_results
                            and sql_info.summary
                        ):
                            sql_section.append(
                                "Result: Large dataset (showing summary)"
                            )
                            sql_section.append(f"Summary: {sql_info.summary}")
                        else:
                            sql_section.append(
                                f"Result: {sql_info.sql_query_result}"
                            )
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

    formatted_input = "\n".join(input_parts)

    return {
        "input": formatted_input,
    }
