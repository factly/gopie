import asyncio

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.log import custom_logger as logger
from app.models.schema import DatasetSchema
from app.services.gopie.dataset_info import get_project_info
from app.services.qdrant.get_schema import (
    get_project_schemas,
    get_schema_from_qdrant,
)
from app.utils.chat_history.processor import ChatHistoryProcessor
from app.utils.langsmith.prompt_manager import get_prompt_llm_chain
from app.workflow.events.event_utils import (
    configure_node,
    fake_streaming_response,
)

from ..types import AgentState


class SQLQuery(BaseModel):
    reasoning_for_relevance: str = Field(description="Reasoning why the query is relevant")
    id: int = Field(description="ID of the query")


class QueryUnderstandingOutput(BaseModel):
    """
    Output from Call 1: Understanding what the user is asking.
    """

    is_follow_up: bool = Field(
        description="Whether this query references or builds upon previous conversation"
    )
    enhanced_query: str = Field(
        description="User's exact query with only ambiguous pronouns resolved"
    )
    context_summary: str = Field(
        description="One sentence about what previous result user is referring to", default=""
    )
    status_message: str = Field(
        description="Brief user-friendly acknowledgment (1-2 sentences)",
        default="",
    )


class DataPlanningOutput(BaseModel):
    """
    Output from Call 2: Deciding what data operations are needed.
    """

    is_new_data_needed: bool = Field(
        description="Whether SQL execution is needed (new or modified query)"
    )
    generate_visualization: bool = Field(
        description="Whether user explicitly requested a visualization"
    )
    previous_sql_queries: list[SQLQuery] = Field(
        description="IDs of relevant SQL queries from history (most recent first)", default=[]
    )
    sql_modification_type: str = Field(
        description="Type of SQL modification needed based on the user's request. Leave empty if no modification is needed.",
        default="",
    )


async def get_projects_with_custom_prompts(
    dataset_ids: list[str] | None,
    project_ids: list[str] | None,
    org_id: str | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, str], list[DatasetSchema]]:
    dataset_schemas = []
    if dataset_ids:
        dataset_tasks = [
            get_schema_from_qdrant(dataset_id=dataset_id) for dataset_id in dataset_ids[:5]
        ]
        dataset_results = await asyncio.gather(*dataset_tasks)
        dataset_schemas = [schema for schema in dataset_results if schema is not None]

    project_schemas = []
    if project_ids:
        project_tasks = [
            get_project_schemas(project_id=project_id, limit=5) for project_id in project_ids
        ]
        project_results = await asyncio.gather(*project_tasks)
        for result in project_results:
            project_schemas.extend(result)

    schemas = dataset_schemas + project_schemas

    project_custom_prompts = {}
    if project_ids:
        project_info_tasks = [
            get_project_info(project_id=project_id, org_id=org_id, user_id=user_id)
            for project_id in project_ids
        ]
        project_info_results = await asyncio.gather(*project_info_tasks, return_exceptions=True)
        for project_id, result in zip(project_ids, project_info_results):
            if not isinstance(result, Exception):
                logger.warning(f"Failed to fetch project info for {project_id}: {result!s}")
                continue
            if result.custom_prompt:
                project_custom_prompts[project_id] = result.custom_prompt

    return project_custom_prompts, schemas[:5]


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
    org_id = config.get("metadata", {}).get("org_id", None)
    user_id = config.get("metadata", {}).get("user", None)
    project_custom_prompts_dict, schemas = await get_projects_with_custom_prompts(
        dataset_ids=dataset_ids, project_ids=project_ids, org_id=org_id, user_id=user_id
    )
    schemas_str = "\n".join(
        [
            f"Schema {i + 1}:\n{schema.format_for_prompt()}"
            for i, schema in enumerate(schemas)
            if schema
        ]
    )

    try:
        # ── Call 1: Query Understanding ──
        query_chain = get_prompt_llm_chain(
            "process_context", config, schema=QueryUnderstandingOutput
        )
        query_understanding = await query_chain.ainvoke(
            {
                "current_query": user_input,
                "formatted_chat_history": formatted_chat_history,
                "project_custom_prompts": project_custom_prompts_dict,
            }
        )

        is_follow_up = query_understanding.is_follow_up
        enhanced_query = query_understanding.enhanced_query
        context_summary = query_understanding.context_summary.strip()

        await fake_streaming_response(query_understanding.status_message, config)

        # ── Call 2: Data Planning ──
        planning_chain = get_prompt_llm_chain("data_planning", config, schema=DataPlanningOutput)
        data_planning = await planning_chain.ainvoke(
            {
                "enhanced_query": enhanced_query,
                "is_follow_up": is_follow_up,
                "context_summary": context_summary,
                "formatted_chat_history": formatted_chat_history,
                "schemas": schemas_str,
            }
        )

        is_new_data_needed = data_planning.is_new_data_needed
        generate_visualization = data_planning.generate_visualization
        previous_sql_queries_ids = [query.id for query in data_planning.previous_sql_queries]
        previous_sql_queries = history_processor.ids_to_sql_queries(ids=previous_sql_queries_ids)
        sql_modification_type = data_planning.sql_modification_type

        if is_follow_up and sql_modification_type and previous_sql_queries:
            final_query = f"[SQL_MODIFICATION: {sql_modification_type}]\n{enhanced_query}"
            if context_summary:
                final_query += f"\n(Context: {context_summary})"
        elif is_follow_up and context_summary:
            final_query = f"{enhanced_query}\n(Context: {context_summary})"
        else:
            final_query = enhanced_query

        if generate_visualization and not (last_vizpaths or previous_sql_queries):
            is_new_data_needed = True

        return {
            "user_query": final_query,
            "new_data_needed": is_new_data_needed,
            "generate_visualization": generate_visualization,
            "relevant_datasets_ids": relevant_datasets_ids,
            "previous_sql_queries": previous_sql_queries,
            "enhanced_query": enhanced_query,
            "previous_json_paths": last_vizpaths,
            "sql_modification_type": sql_modification_type,
        }

    except Exception as e:
        logger.exception(f"Error processing context: {e!s}")
        return {
            "user_query": user_input,
            "new_data_needed": True,
            "generate_visualization": False,
            "relevant_datasets_ids": relevant_datasets_ids,
            "previous_sql_queries": [],
            "enhanced_query": user_input,
            "previous_json_paths": last_vizpaths,
            "sql_modification_type": "",
        }
