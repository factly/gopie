from langchain.schema.runnable import RunnableConfig
from langchain_core.callbacks import adispatch_custom_event

from app.core.log import custom_logger as logger
from app.models.message import IntermediateStep
from app.services.qdrant.duckdb_docs.search import (
    format_duckdb_docs_context,
    get_duckdb_docs,
)
from app.workflow.events.event_utils import configure_node

from .types import State


@configure_node(
    role="intermediate",
    progress_message="🔍 Searching DuckDB documentation for relevant information...",
)
async def search_duckdb_docs(state: State, config: RunnableConfig) -> dict:
    """
    Search DuckDB documentation based on error context.

    This node is invoked when SQL generation fails. It searches the DuckDB
    documentation vector store for relevant information and adds it to the
    state for use in retry attempts.

    Args:
        state: Current state with error context
        config: Runnable configuration

    Returns:
        Updated state with DuckDB documentation context
    """
    user_query = state.get("user_query", "")
    validation_result = state.get("validation_result", "")

    try:
        docs = await get_duckdb_docs(search_query=validation_result or user_query)

        if docs:
            duckdb_context = format_duckdb_docs_context(docs)
            msg = "Gathered relevant DuckDB documentation!"
            await adispatch_custom_event(
                "gopie-agent",
                {"content": msg},
            )

            return {
                "duckdb_docs_context": duckdb_context,
                "messages": [IntermediateStep(content=msg)],
            }
        else:
            msg = "No relevant DuckDB documentation found."
            await adispatch_custom_event(
                "gopie-agent",
                {"content": msg},
            )

            return {
                "duckdb_docs_context": "",
                "messages": [IntermediateStep(content=msg)],
            }

    except Exception as e:
        error_msg = f"Error searching DuckDB documentation: {e!s}"
        logger.exception(error_msg)

        await adispatch_custom_event(
            "gopie-agent",
            {"content": "Error searching DuckDB documentation."},
        )

        return {
            "duckdb_docs_context": "",
            "messages": [IntermediateStep(content=error_msg)],
        }


def should_search_duckdb_docs(state: State) -> str:
    if state.get("validation_result"):
        return "search_docs"
    return "generate_sql"
