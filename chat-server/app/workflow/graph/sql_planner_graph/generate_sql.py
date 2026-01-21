from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.log import custom_logger as logger
from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import SqlQueryInfo
from app.utils.langsmith.prompt_manager import get_prompt_llm_chain

from .types import State


class SqlQueryOutput(BaseModel):
    sql_query: str = Field(
        description="The SQL SELECT query. No semicolon. DuckDB-compatible. Double-quote identifiers.",
    )
    explanation: str = Field(
        description="Short technical explanation: query strategy, key columns, JOIN approach if multiple tables, and what the result represents.",
    )
    tables_used: list[str] = Field(
        description="Exact table names from the schema used in this query (e.g. gp_xxx).",
    )


class PlanQueryOutput(BaseModel):
    sql_queries: list[SqlQueryOutput] = Field(
        description="List of SQL queries to execute. Use [] when not generating SQL (Path B).",
        default=[],
    )
    non_sql_response: str = Field(
        description="ONLY when NOT generating SQL (Path B): technical explanation why no SQL. MUST be empty string '' when sql_queries is non-empty.",
        default="",
    )
    user_friendly_response: str = Field(
        description="ONLY when NOT generating SQL (Path B): short user message (<200 chars) why no query. MUST be empty string '' when sql_queries is non-empty.",
        default="",
    )
    limitations: str = Field(
        description="Always required. 1-2 sentences: assumptions (join keys, same ID across tables), missing data, units, or exclusions.",
        default="",
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
        non_sql_response = response.non_sql_response or ""
        limitations = response.limitations or ""
        user_friendly_response = response.user_friendly_response or ""

        # Defensive: if model generated SQL, treat as Path A and ignore non_sql/user_friendly
        # (avoids dropping SQL when model wrongly fills both paths)
        if sql_queries:
            non_sql_response = ""
            user_friendly_response = ""

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
