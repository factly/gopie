from langchain.schema.runnable import RunnableConfig
from langchain_core.callbacks import adispatch_custom_event
from pydantic import BaseModel, Field

from app.core.log import custom_logger as logger
from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import SqlQueryInfo
from app.utils.langsmith.prompt_manager import get_prompt_llm_chain

from .types import State


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
    non_sql_response: str = Field(
        description="Clear explanation when SQL queries cannot be generated", default=""
    )
    user_friendly_response: str = Field(
        description="A short user friendly (no technical jargon or error messages revealed in this field) "
        "message not more than 200 characters telling why there was no SQL query generated otherwise this field should be empty",
        default="",
    )
    limitations: str = Field(
        description="Any constraints or assumptions in the analysis", default=""
    )


async def generate_sql(state: State, config: RunnableConfig) -> dict:
    """
    Plan SQL queries based on user input and dataset information.

    This function is compatible with both single-dataset and multi-dataset modes.
    It generates SQL queries or provides non-SQL responses based on the user's query
    and available dataset information.

    Args:
        state: The current state containing user query, datasets info, mode, and other context
        config: Runnable configuration for LLM chain

    Returns:
        Updated state with planned SQL queries or non-SQL response
    """
    user_query = state.get("user_query", "No input")
    multi_datasets_info = state.get("multi_datasets_info", {})
    single_dataset_info = state.get("single_dataset_info", {})
    retry_count = state.get("retry_count", 0)
    prev_sql_queries = state.get("prev_sql_queries", [])
    validation_result = state.get("validation_result", None)
    duckdb_docs_context = state.get("duckdb_docs_context", "")

    try:
        if not multi_datasets_info and not single_dataset_info:
            raise Exception("No dataset information provided")

        chain_input = {
            "user_query": user_query,
            "datasets_info": multi_datasets_info or single_dataset_info,
            "retry_count": retry_count,
            "prev_sql_queries": prev_sql_queries,
            "validation_result": validation_result,
            "duckdb_docs_context": duckdb_docs_context,
        }

        chain = get_prompt_llm_chain("generate_sql", config, schema=PlanQueryOutput)
        response = await chain.ainvoke(chain_input)

        sql_queries = response.sql_queries
        non_sql_response = response.non_sql_response
        limitations = response.limitations
        user_friendly_response = response.user_friendly_response
        if non_sql_response:
            await adispatch_custom_event(
                "gopie-agent",
                {
                    "content": user_friendly_response or "No SQL query generated",
                },
            )

            return {
                "sql_queries": [],
                "non_sql_response": non_sql_response,
                "user_friendly_response": user_friendly_response,
                "limitations": limitations,
                "tables_used": [],
                "messages": [IntermediateStep.from_json(response.model_dump())],
            }
        elif sql_queries:
            sql_queries_info: list[SqlQueryInfo] = []
            tables_used = []

            for sql_query in sql_queries:
                sql_queries_info.append(
                    SqlQueryInfo(
                        sql_query=sql_query.sql_query,
                        explanation=sql_query.explanation,
                    )
                )
                tables_used.extend(sql_query.tables_used)

            return {
                "sql_queries": sql_queries_info,
                "non_sql_response": None,
                "user_friendly_response": user_friendly_response,
                "limitations": limitations,
                "tables_used": list(set(tables_used)),
                "messages": [IntermediateStep.from_json(response.model_dump())],
            }
        else:
            raise Exception(
                "Invalid response: must contain either 'sql_queries' or 'non_sql_response'"
            )

    except Exception as e:
        error_msg = f"Unexpected error in query planning: {e!s}"

        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "Error in query planning",
            },
        )

        logger.exception(error_msg)

        return {
            "sql_queries": [],
            "non_sql_response": None,
            "messages": [ErrorMessage(content=error_msg)],
        }
