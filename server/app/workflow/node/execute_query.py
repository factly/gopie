from app.core.config import settings
from app.core.langchain_config import lc
from app.models.message import ErrorMessage, IntermediateStep
from app.utils.sql_executor import execute_sql
from app.workflow.graph.types import State


async def execute_query(state: State) -> dict:
    """
    Execute the planned query using the external SQL API

    Args:
        state: The current state object containing messages and
               query information

    Returns:
        Updated state with query results or error messages
    """
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    try:
        last_message = (
            state.get("messages", [])[-1] if state.get("messages") else None
        )
        if not last_message or isinstance(last_message, ErrorMessage):
            raise ValueError("No valid query plan found in messages")

        query_plan = last_message.content[0]

        if not query_plan:
            raise ValueError("Failed to parse query plan from message")

        sql_query = query_plan.get("sql_query")
        if not sql_query:
            raise ValueError("No SQL query found in plan")

        result = await execute_sql(sql_query)

        if isinstance(result, dict) and "error" in result:
            raise ValueError(result["error"])

        result_records = result

        result_dict = {
            "result": "Query executed successfully",
            "query_executed": sql_query,
            "data": result_records,
        }

        query_result.subqueries[query_index].sql_query_used = sql_query
        query_result.subqueries[query_index].query_result = result_records

        return {
            "query_result": query_result,
            "messages": [IntermediateStep.from_json(result_dict)],
        }

    except Exception as e:
        error_msg = f"Query execution error: {e!s}"
        query_result.add_error_message(error_msg, "Query execution")

        return {
            "query_result": query_result,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
            "retry_count": state.get("retry_count", 0) + 1,
        }


async def route_query_replan(state: State) -> str:
    """
    Determine whether to replan the query or generate results based on
    execution status

    Args:
        state: The current state containing messages and retry information

    Returns:
        Routing decision: "replan", "reidentify_datasets", or
        "validate_query_result"
    """
    last_message = state["messages"][-1]
    retry_count = state.get("retry_count", 0)

    if (
        isinstance(last_message, ErrorMessage)
        and retry_count < settings.MAX_RETRY_COUNT
    ):
        response = await lc.llm.ainvoke(
            {
                "input": f"""
                I got an error when executing the query:
                "{last_message.content}"

                Can you please tell whether this error can be solved by
                replanning the query? or it's need to reidentify the datasets?

                If it's need to reidentify the datasets, please return
                "reidentify_datasets"
                If it's need to replan the query, please return "replan"
                If it's no problem, please return "validate_query_result"

                Think through this step-by-step:
                1. Analyze the error message
                2. Determine if it's a schema/dataset issue
                3. Check if it's a query syntax issue
                4. Decide on the appropriate action
            """
            }
        )

        response_text = str(response.content).lower()

        if "reidentify_datasets" in response_text:
            return "reidentify_datasets"
        elif "replan" in response_text:
            return "replan"
        else:
            return "validate_query_result"

    return "validate_query_result"
