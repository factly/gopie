from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.models.message import ErrorMessage, IntermediateStep
from app.utils.model_provider import model_provider
from app.workflow.graph.types import State
from app.workflow.prompts.prompt_selector import get_prompt


async def plan_query(state: State, config: RunnableConfig) -> dict:
    """
    Plan the SQL query based on user input and dataset information.
    This function generates a SQL query that addresses the user's question
    using the available dataset information.

    Args:
        state: The current state containing datasets, user query, and other
        context

    Returns:
        Updated state with the planned SQL query and related information
    """
    try:
        identified_datasets = state.get("identified_datasets", [])
        query_index = state.get("subquery_index", 0)
        user_query = (
            state.get("subqueries")[query_index]
            if state.get("subqueries")
            else "No input"
        )
        query_result = state.get("query_result", {})
        datasets_info = state.get("datasets_info", {})

        if not identified_datasets:
            raise Exception("No dataset selected for query planning")

        retry_count = query_result.subqueries[query_index].retry_count
        error_messages = query_result.subqueries[query_index].error_message

        if not identified_datasets:
            raise Exception("No dataset selected for query planning")

        if not datasets_info:
            raise Exception(
                "Could not get preview information for any of the selected "
                "datasets"
            )

        llm_prompt = get_prompt(
            "plan_query",
            user_query=user_query,
            datasets_info=datasets_info,
            error_message=error_messages,
            attempt=retry_count + 1,
        )

        llm = model_provider(config=config).get_llm()
        response = await llm.ainvoke({"input": llm_prompt})
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
            formatted_sql_query = parsed_response.get(
                "formatted_sql_query", sql_query
            )

            if not sql_query:
                raise Exception("Failed in parsing SQL query")

            query_result.subqueries[query_index].sql_query_used = sql_query
            query_result.subqueries[
                query_index
            ].sql_query_explanation = sql_query_explanation

            await adispatch_custom_event(
                "dataful-agent",
                {
                    "content": "Generated SQL query",
                    "query": formatted_sql_query,
                },
            )

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

        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": "Error in query planning",
                "query": None,
            },
        )

        return {
            "query_result": query_result,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }
