from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_model_provider,
)
from app.workflow.events.event_utils import configure_node

from ..types import AgentState, Dataset


@configure_node(
    role="intermediate",
    progress_message="Processing chat context...",
)
async def process_context(state: AgentState, config: RunnableConfig) -> dict:
    user_input = state.get("initial_user_query", "")
    chat_history = get_chat_history(config) or []
    dataset_ids = state.get("dataset_ids", [])

    prompt_messages = get_prompt(
        "process_context",
        current_query=user_input,
        dataset_ids=dataset_ids,
    )

    llm = get_model_provider(config).get_llm_for_node("process_context")
    response = await llm.ainvoke(chat_history + prompt_messages)

    try:
        parser = JsonOutputParser()
        parsed_response = parser.parse(str(response.content))

        is_follow_up = parsed_response.get("is_follow_up", False)
        new_data_needed = parsed_response.get("new_data_needed", False)
        needs_visualization = parsed_response.get("needs_visualization", False)
        visualization_data = parsed_response.get("visualization_data", [])
        previous_json_paths = parsed_response.get("previous_json_paths", [])
        relevant_datasets_ids = parsed_response.get("relevant_datasets_ids", [])
        relevant_sql_queries = parsed_response.get("relevant_sql_queries", [])
        enhanced_query = parsed_response.get("enhanced_query", user_input)
        context_summary = parsed_response.get("context_summary", "")

        final_query = f"""
The original user query and the previous conversation history were processed
and the following context summary was added to the query:

{is_follow_up and "This is a follow-up question to a previous query." or ""}

User Query: {enhanced_query}

Context Summary: {context_summary}
"""
        datasets = []
        if visualization_data:
            for viz_data in visualization_data:
                if isinstance(viz_data, dict) and "data" in viz_data and "description" in viz_data:
                    dataset = Dataset(
                        data=viz_data["data"],
                        description=viz_data["description"],
                        csv_path=viz_data.get("csv_path"),
                    )
                    datasets.append(dataset)

        return {
            "user_query": final_query,
            "new_data_needed": new_data_needed,
            "needs_visualization": needs_visualization,
            "visualization_data": visualization_data,
            "previous_json_paths": previous_json_paths,
            "relevant_datasets_ids": relevant_datasets_ids,
            "relevant_sql_queries": relevant_sql_queries,
            "datasets": datasets,
        }

    except Exception as e:
        logger.error(f"Error processing context: {e!s}")
        return {"user_query": user_input}
