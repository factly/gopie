from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import RunnableConfig

from app.core.log import custom_logger as logger
from app.models.message import IntermediateStep
from app.services.qdrant.duckdb_docs.search import (
    format_duckdb_docs_context,
    get_duckdb_docs,
)
from app.utils.olap import is_duckdb_family
from app.workflow.events.event_utils import configure_node
from app.workflow.prompts.db_prompts import get_db_name

from .types import State


@configure_node(
    role="intermediate",
    progress_message="🔍 Searching database documentation for relevant information...",
)
async def search_db_docs(state: State, config: RunnableConfig) -> dict:
    """
    Search database documentation based on error context.

    This node is invoked when SQL generation fails. It searches the appropriate
    documentation vector store for relevant information and adds it to the
    state for use in retry attempts.

    For DuckDB: Searches DuckDB documentation in Qdrant
    For ClickHouse: Currently skips (no docs indexed yet)

    Args:
        state: Current state with error context
        config: Runnable configuration

    Returns:
        Updated state with database documentation context
    """
    user_query = state.get("user_query", "")
    validation_result = state.get("validation_result", "")
    db_name = get_db_name()

    # Only search DuckDB docs for DuckDB family databases
    # ClickHouse docs are not yet indexed in Qdrant
    if not is_duckdb_family():
        msg = f"Documentation search not available for {db_name}."
        await adispatch_custom_event(
            "gopie-agent",
            {"content": msg},
        )
        return {
            "duckdb_docs_context": "",
            "messages": [IntermediateStep(content=msg)],
        }

    try:
        docs = await get_duckdb_docs(search_query=validation_result or user_query)

        if docs:
            duckdb_context = format_duckdb_docs_context(docs)
            msg = f"Gathered relevant {db_name} documentation!"
            await adispatch_custom_event(
                "gopie-agent",
                {"content": msg},
            )

            return {
                "duckdb_docs_context": duckdb_context,
                "messages": [IntermediateStep(content=msg)],
            }
        else:
            msg = f"No relevant {db_name} documentation found."
            await adispatch_custom_event(
                "gopie-agent",
                {"content": msg},
            )

            return {
                "duckdb_docs_context": "",
                "messages": [IntermediateStep(content=msg)],
            }

    except Exception as e:
        error_msg = f"Error searching {db_name} documentation: {e!s}"
        logger.exception(error_msg)

        await adispatch_custom_event(
            "gopie-agent",
            {"content": f"Error searching {db_name} documentation."},
        )

        return {
            "duckdb_docs_context": "",
            "messages": [IntermediateStep(content=error_msg)],
        }


# Keep the old function name as alias for backward compatibility
search_duckdb_docs = search_db_docs


def should_search_db_docs(state: State) -> str:
    if state.get("validation_result"):
        return "search_docs"
    return "generate_sql"


# Keep the old function name as alias for backward compatibility
should_search_duckdb_docs = should_search_db_docs
