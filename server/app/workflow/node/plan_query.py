import json

from langchain_core.output_parsers import JsonOutputParser

from app.core.langchain_config import lc
from app.models.message import ErrorMessage, IntermediateStep
from app.workflow.graph.types import State


def create_query_prompt(
    user_query: str,
    datasets_info: dict,
    error_message: str | dict,
    attempt: int = 1,
) -> str:
    error_context = ""
    if error_message and attempt > 1:
        error_context = f"""
        Previous attempt failed with this error:
        {error_message}

        Please fix the issues in the query and try again. This is attempt
        {attempt} of 3.
        """
    return f"""
        Given the following natural language query and detailed information
        about multiple datasets, create an appropriate SQL query.

        User Query: "{user_query}"

        Selected Datasets Information:
        {json.dumps(datasets_info, indent=2)}

        IMPORTANT - DATASET NAMING:
        - Each dataset has a 'name' (user-friendly name) and an 'dataset_name'
          (the real table name in the database)
        - In your SQL query, you MUST use the dataset_name from the
          datasets_info
        - Example: If a dataset is shown as "COVID-19 Cases" to the user, its
          actual table name might be "ASD_ASDRDasdfaW"
        - Reference the provided `dataset_name_mapping` for the correct mapping

        Error Context: {error_context}

        IMPORTANT GUIDELINES:
        1. Use the EXACT column names as shown in the dataset information
        2. Create a query that directly addresses the user's question
        3. If the user's query refers to a time period that doesn't match the
           dataset format (e.g., asking for 2018 when dataset uses 2018-19),
           adapt accordingly
        4. Make sure to handle column names correctly, matching the exact names
           in the dataset metadata
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


async def plan_query(state: State) -> dict:
    """
    Plan the SQL query based on user input and dataset information.
    Makes a single attempt at query planning, handling various error
    conditions gracefully.
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
        datasets_info = state.get("datasets_info", {})

        retry_count = state.get("retry_count", 0)

        if not selected_datasets:
            raise Exception("No dataset selected for query planning")

        last_message = state.get("messages", [])[-1]
        last_error = (
            last_message.content[0]
            if isinstance(last_message, ErrorMessage)
            else ""
        )

        if not selected_datasets:
            raise Exception("No dataset selected for query planning")

        if not datasets_info:
            raise Exception(
                "Could not get preview information for any of the selected "
                "datasets"
            )

        llm_prompt = create_query_prompt(
            user_query, datasets_info, last_error, retry_count + 1
        )

        response = await lc.llm.ainvoke(llm_prompt)
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
                field
                for field in required_fields
                if field not in parsed_response
            ]

            if missing_fields:
                raise Exception(
                    f"Missing required fields in LLM response: "
                    f"{', '.join(missing_fields)}"
                )

            sql_query = parsed_response.get("sql_query", "")
            sql_query_explanation = parsed_response.get("explanation", "")

            if not sql_query:
                raise Exception("Failed in parsing SQL query")

            query_result.subqueries[query_index].sql_query_used = sql_query
            query_result.subqueries[
                query_index
            ].sql_query_explanation = sql_query_explanation

            return {
                "query_result": query_result,
                "query": sql_query,
                "messages": [IntermediateStep.from_json(parsed_response)],
            }

        except Exception as parse_error:
            raise Exception(
                f"Failed to parse LLM response: {parse_error!s}"
            ) from parse_error

    except Exception as e:
        query_result.add_error_message(str(e), "Error in query planning")
        error_msg = f"Unexpected error in query planning: {e!s}"
        return {
            "query_result": query_result,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }
