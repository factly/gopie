import asyncio

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.log import logger
from app.models.schema import DatasetSchema
from app.services.qdrant.get_schema import (
    get_project_schema,
    get_schema_from_qdrant,
)
from app.utils.chat_history.processor import ChatHistoryProcessor
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_configured_llm_for_node
from app.workflow.events.event_utils import configure_node

from ..types import AgentState


class SQLQuery(BaseModel):
    reasoning_for_relevance: str = Field(description="Reasoning why the query is relevant")
    id: int = Field(description="ID of the query")


class ProcessContextOutput(BaseModel):
    is_follow_up: bool = Field(
        description="Whether this is a follow-up query from conversation history"
    )
    is_new_data_needed: bool = Field(
        description="Whether new data retrieval is needed to answer the query"
    )
    is_visualization_query: bool = Field(
        description="Whether the query is related to visualization"
    )
    relevant_sql_queries: list[SQLQuery] = Field(
        description="Most relevant SQL queries from previously used queries", default=[]
    )
    enhanced_query: str = Field(
        description="Self-contained and unambiguous rewritten query with context"
    )
    context_summary: str = Field(
        description="Summary of how the present query relates to previous conversation", default=""
    )


async def get_project_custom_prompts(
    dataset_ids: list[str], project_ids: list[str]
) -> tuple[list[str], list[DatasetSchema]]:
    tasks = [get_schema_from_qdrant(dataset_id) for dataset_id in dataset_ids]
    for project_id in project_ids:
        tasks.append(get_project_schema(project_id))
    schemas = await asyncio.gather(*tasks)
    project_custom_prompts = []
    for schema in schemas:
        if schema:
            if schema.project_custom_prompt:
                project_custom_prompts.append(schema.project_custom_prompt)
    return list(set(project_custom_prompts)), schemas


@configure_node(
    role="intermediate",
    progress_message="Processing chat context...",
)
async def process_context(state: AgentState, config: RunnableConfig) -> dict:
    user_input = state.get("initial_user_query", "")

    history_processor = ChatHistoryProcessor(config)

    history_context = history_processor.get_context_summary()
    formatted_chat_history = history_context["formatted_history"]
    last_vizpaths = history_context["vizpaths"]
    relevant_datasets_ids = history_context["datasets_used"]
    dataset_ids = state.get("dataset_ids", [])
    project_ids = state.get("project_ids", [])
    project_custom_prompts, schemas = await get_project_custom_prompts(dataset_ids, project_ids)
    prompt_messages = get_prompt(
        "process_context",
        current_query=user_input,
        formatted_chat_history=formatted_chat_history,
        project_custom_prompts=project_custom_prompts,
        schemas="\n".join([schema.format_for_prompt() for schema in schemas if schema]),
    )

    llm = get_configured_llm_for_node("process_context", config, schema=ProcessContextOutput)

    try:
        parsed_response = await llm.ainvoke(prompt_messages)

        is_follow_up = parsed_response.is_follow_up
        is_new_data_needed = parsed_response.is_new_data_needed
        needs_visualization = parsed_response.is_visualization_query
        relevant_sql_queries_ids = [query.id for query in parsed_response.relevant_sql_queries]
        relevant_sql_queries = history_processor.ids_to_sql_queries(relevant_sql_queries_ids)
        enhanced_query = parsed_response.enhanced_query
        context_summary = parsed_response.context_summary

        if is_follow_up:
            final_query = f"""
            This is a follow-up question to a previous query.

            User Query: {enhanced_query}

            Context Summary: {context_summary}
            """
        else:
            final_query = enhanced_query

        return {
            "user_query": final_query,
            "new_data_needed": is_new_data_needed,
            "needs_visualization": needs_visualization,
            "relevant_datasets_ids": relevant_datasets_ids,
            "relevant_sql_queries": relevant_sql_queries,
            "enhanced_query": enhanced_query,
            "previous_json_paths": last_vizpaths,
        }

    except Exception as e:
        logger.error(f"Error processing context: {e!s}")
        return {
            "user_query": user_input,
            "new_data_needed": True,
            "needs_visualization": False,
            "relevant_datasets_ids": relevant_datasets_ids,
            "relevant_sql_queries": [],
            "enhanced_query": user_input,
            "previous_json_paths": last_vizpaths,
        }
