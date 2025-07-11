import json

from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.models.message import AIMessage, ErrorMessage
from app.models.query import QueryResult
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.multi_dataset_graph.types import State


@configure_node(
    role="ai",
    progress_message="",
)
async def generate_result(state: State, config: RunnableConfig) -> dict:
    """
    Generate a response based on the query result
    """

    query_result = state.get("query_result")
    if query_result:
        if isinstance(query_result, QueryResult):
            query_result.calculate_execution_time()

        logger.debug(
            "query_result: %s",
            json.dumps(query_result.to_dict(), indent=2, default=str),
        )

    try:
        if not isinstance(query_result, QueryResult):
            return {
                "messages": [
                    ErrorMessage.from_json(
                        {
                            "error": "Invalid query result format",
                            "details": "Expected QueryResult object",
                        }
                    )
                ]
            }

        prompt = get_prompt(
            node_name="generate_result",
            query_result=query_result,
        )

        llm = get_model_provider(config).get_llm_for_node("generate_result")
        response = await llm.ainvoke(prompt)

        return {
            "messages": [
                AIMessage(
                    content=[
                        {
                            "result": str(response.content),
                            "execution_time": query_result.execution_time,
                        }
                    ]
                )
            ],
            "query_result": query_result,
            "response_text": str(response.content),
        }
    except Exception as e:
        return {
            "messages": [
                ErrorMessage.from_json(
                    {
                        "error": "Critical error in result generation",
                        "details": str(e),
                    }
                )
            ]
        }
