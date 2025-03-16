import json

from langchain_core.output_parsers import JsonOutputParser

from src.lib.config.langchain_config import lc
from src.lib.graph.types import ErrorMessage, IntermediateStep, State


def create_query_prompt(
    user_query: str,
    datasets_info: dict,
    error_message: str = "",
    attempt: int = 1,
) -> str:
    """Create a prompt for the LLM to generate a SQL query"""
    error_context = ""
    if error_message and attempt > 1:
        error_context = f"""
        Previous attempt failed with this error:
        {error_message}

        Please fix the issues in the query and try again. This is attempt {attempt} of 3.
        """
    return f"""
        Given the following natural language query and detailed information about multiple datasets, create an appropriate SQL query.

        User Query: "{user_query}"

        Selected Datasets Information:
        {json.dumps(datasets_info, indent=2)}

        Error Context: {error_context}

        IMPORTANT GUIDELINES:
        1. Use the EXACT column names as shown in the dataset information
        2. Create a query that directly addresses the user's question
        3. If the user's query refers to a time period that doesn't match the dataset format (e.g., asking for 2018 when dataset uses 2018-19), adapt accordingly
        4. Make sure to handle column names correctly, matching the exact names in the dataset metadata
        5. Use the sample data as reference for the data format and values
        6. If the query requires joining multiple datasets, make sure to:
           - Use appropriate join conditions
           - Handle potentially conflicting column names
           - Specify table aliases if needed
           - Consider the relationship between datasets

        Respond in this JSON format:
        {{
            "sql_query": "the SQL query to fetch the required data",
            "explanation": "brief explanation of what the query does",
            "tables_used": ["list of tables needed"],
            "joins_required": [
                {{
                    "left_table": "name of left table",
                    "right_table": "name of right table",
                    "join_type": "type of join (INNER, LEFT, etc.)",
                    "join_conditions": ["list of join conditions"]
                }}
            ],
            "expected_result": "description of what the query will return"
        }}
    """


def plan_query(state: State) -> dict:
    """
    Plan the SQL query based on user input and dataset information.
    Makes a single attempt at query planning, handling various error conditions gracefully.
    Uses all selected datasets and their relationships.
    """
    try:
        selected_datasets = state.get("datasets", [])
        query_index = state.get("subquery_index", 0)
        user_query = (
            state.get("subqueries")[query_index]
            if state.get("subqueries")
            else "No input"
        )
        query_result = state.get("query_result", {})
        datasets_info = state.get("dataset_info", {})

        retry_count = state.get("retry_count", 0)

        if not selected_datasets:
            raise Exception("No dataset selected for query planning")

        # This error message might be from execute_query node or analyze_dataset node
        last_message = state.get("messages", [])[-1]
        last_error = (
            str(last_message.content) if isinstance(last_message, ErrorMessage) else ""
        )

        if not selected_datasets:
            raise Exception("No dataset selected for query planning")

        if not datasets_info:
            raise Exception(
                "Could not get preview information for any of the selected datasets"
            )

        llm_prompt = create_query_prompt(
            user_query, datasets_info, last_error, retry_count + 1
        )

        response = lc.llm.invoke(llm_prompt)
        response_content = str(response.content)

        parser = JsonOutputParser()
        try:
            parsed_response = parser.parse(response_content)

            required_fields = [
                "sql_query",
                "explanation",
                "tables_used",
                "expected_result",
            ]
            missing_fields = [
                field for field in required_fields if field not in parsed_response
            ]

            if missing_fields:
                raise Exception(
                    f"Missing required fields in LLM response: {', '.join(missing_fields)}"
                )

            sql_query = parsed_response.get("sql_query", "")

            if not sql_query:
                raise Exception("Failed in parsing SQL query")

            query_result.subqueries[query_index].sql_query_used = sql_query

            return {
                "query_result": query_result,
                "query": sql_query,
                "messages": [
                    IntermediateStep.from_text(json.dumps(parsed_response, indent=2))
                ],
            }

        except Exception as parse_error:
            raise Exception(f"Failed to parse LLM response: {str(parse_error)}")

    except Exception as e:
        query_result.add_error_message(str(e), "Error in query planning")
        error_msg = f"Unexpected error in query planning: {str(e)}"
        return {
            "query_result": query_result,
            "messages": [
                ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))
            ],
        }
