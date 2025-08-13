from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import SqlQueryInfo
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_configured_llm_for_node
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.multi_dataset_graph.types import State


class SqlQueryOutput(BaseModel):
    sql_query: str = Field(description="SQL query without semicolon, compatible with DuckDB")
    explanation: str = Field(
        description="""concise explanation including: Query strategy (e.g., filtering by X to get Y),
        key columns used and their data types, table metadata (table name, what data it contains),
        JOIN strategy if multiple tables, and expected result format"""
    )
    tables_used: list[str] = Field(description="List of table names used in the query")


class PlanQueryOutput(BaseModel):
    sql_queries: list[SqlQueryOutput] = Field(
        description="List of SQL queries to execute", default=[]
    )
    response_for_no_sql: str = Field(
        description="Clear explanation when SQL queries cannot be generated", default=""
    )
    limitations: str = Field(
        description="Any constraints or assumptions in the analysis", default=""
    )


@configure_node(
    role="intermediate",
    progress_message="Planning query...",
)
async def plan_query(state: State, config: RunnableConfig) -> dict:
    """
    Plan the SQL query based on user input and dataset information.
    This function generates a SQL query or multiple queries that address
    the user's question using the available dataset information.

    It will generate:
    - A single SQL query with JOINs if datasets are related
    - Multiple SQL queries if datasets are not related

    Args:
        state: The current state containing datasets, user query, and other
        context

    Returns:
        Updated state with the planned SQL query/queries
    """

    identified_datasets = state.get("identified_datasets", [])
    query_index = state.get("subquery_index", 0)
    user_query = state.get("subqueries")[query_index] if state.get("subqueries") else "No input"
    query_result = state.get("query_result", {})
    datasets_info = state.get("datasets_info", {})
    previous_sql_queries = state.get("previous_sql_queries", [])
    validation_result = state.get("validation_result", None)

    # Reset the SQL queries and tables used for the current subquery (due to validation logic)
    query_result.subqueries[query_index].sql_queries = []
    query_result.subqueries[query_index].tables_used = None

    try:
        if not identified_datasets:
            raise Exception("No dataset selected for query planning")

        retry_count = query_result.subqueries[query_index].retry_count
        error_messages = query_result.subqueries[query_index].error_message

        if not identified_datasets:
            raise Exception("No dataset selected for query planning")

        if not datasets_info:
            raise Exception("Could not get preview information for any of the selected datasets")

        llm_prompt = get_prompt(
            "plan_query",
            user_query=user_query,
            datasets_info=datasets_info,
            error_messages=error_messages,
            retry_count=retry_count,
            previous_sql_queries=previous_sql_queries,
            validation_result=validation_result,
        )

        llm = get_configured_llm_for_node("plan_query", config, schema=PlanQueryOutput)
        response = await llm.ainvoke(llm_prompt)

        sql_queries = response.sql_queries
        response_for_no_sql = response.response_for_no_sql
        limitations = response.limitations

        if response_for_no_sql:
            query_result.subqueries[query_index].no_sql_response = response_for_no_sql

            query_result.set_node_message(
                "plan_query",
                {
                    "query_strategy": "no_sql_response",
                    "no_sql_response": response_for_no_sql,
                    "limitations": limitations,
                },
            )
        elif sql_queries:
            formatted_sql_queries = []
            sql_queries_info = []

            for sql_query in sql_queries:
                sql_queries_info.append(
                    SqlQueryInfo(
                        sql_query=sql_query.sql_query,
                        explanation=sql_query.explanation,
                    )
                )

                formatted_sql_queries.append(sql_query.sql_query)

            query_result.subqueries[query_index].sql_queries = sql_queries_info

            tables_used = []
            for query in sql_queries:
                tables_used.extend(query.tables_used)

            query_result.set_node_message(
                "plan_query",
                {
                    "query_strategy": (
                        "single_query" if len(sql_queries) == 1 else "multiple_queries"
                    ),
                    "tables_used": list(set(tables_used)),
                    "query_count": len(sql_queries),
                    "limitations": limitations,
                },
            )
        else:
            raise Exception(
                "Invalid response: must contain either 'sql_queries' or 'response_for_no_sql'"
            )

        return {
            "query_result": query_result,
            "messages": [IntermediateStep.from_json(response.model_dump())],
        }

    except Exception as e:
        error_msg = f"Unexpected error in query planning: {e!s}"
        query_result.add_error_message(error_msg, "Error in query planning")

        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "Error in query planning",
            },
        )

        return {
            "query_result": query_result,
            "messages": [ErrorMessage(content=error_msg)],
        }
