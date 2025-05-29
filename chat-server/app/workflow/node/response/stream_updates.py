import json

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.types import State


async def stream_updates(state: State, config: RunnableConfig) -> dict:
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    subquery_result = query_result.subqueries[query_index]
    sql_queries = [
        sql_info.sql_query for sql_info in subquery_result.sql_queries
    ]
    node_messages = subquery_result.node_messages

    stream_update_prompt = f"""
    I need to create a brief update about the execution of a subquery.

    Original User Query: "{query_result.original_user_query}"

    This is subquery {query_index + 1} / {len(query_result.subqueries)}:
    "{subquery_result.query_text}"

    SQL Queries Used:
    {json.dumps(sql_queries, indent=2)}

    Subquery Result Information:
    {json.dumps(subquery_result.to_dict())}

    Node Messages:
    {json.dumps(node_messages, indent=2)}

    Error Information (if any):
    {json.dumps(subquery_result.error_message)}

    Remaining Subqueries:
    {
        json.dumps([
            sq.query_text
            for sq in query_result.subqueries[query_index + 1:]
        ])
    }

    INSTRUCTIONS:
    1. First, determine if this subquery was successful or failed by examining
       the data.
    2. If the subquery FAILED:
       - Explain in simple terms why it failed
       - Analyze if this failure is critical for the remaining subqueries
       - Clearly state if execution should continue or stop
       - Be professional but empathetic about the failure

    3. If the subquery was SUCCESSFUL:
       - Provide a clear and concise summary of the results
       - Focus on the actual data retrieved and its relevance to the user's
         question
       - Highlight any interesting patterns or insights
       - Don't describe the execution process, focus on what was found

    4. Keep your response concise (2-3 sentences)
    5. End by stating the next action (continue to next subquery, stopping
       execution, etc.)

    Your response should be informative, actionable, and user-friendly.
    """

    llm = get_llm_for_node("stream_updates", config)
    response = await llm.ainvoke(
        {
            "input": stream_update_prompt,
            "chat_history": get_chat_history(config),
        }
    )

    logger.debug(f"Stream updates response: {response.content}")

    return {"messages": [AIMessage(content=response.content)]}


async def check_further_execution_requirement(
    state: State, config: RunnableConfig
) -> str:
    """
    Determines if further execution is required based on the current state.
    Returns a string indicating the next step: "next_sub_query" or
    "end_execution".
    """
    await adispatch_custom_event(
        "dataful-agent",
        {
            "content": "do not stream",
        },
    )

    last_stream_message = state.get("messages", [])[-1]

    analysis_prompt = f"""
        Analyze this message about a subquery execution and determine if
        further execution should continue.
        execution should continue.

        Message: {last_stream_message.content}

        Make a decision based on:
        1. If the message explicitly states to continue or stop
        2. If the message mentions or implies a critical failure
        3. If the message indicates an error that prevents further processing
        4. Whether the remaining subqueries can still provide value

        Return a JSON object with:
        {{
            "continue_execution": true/false,
            "reasoning": "brief explanation"
        }}
    """

    llm = get_llm_for_node("check_further_execution_requirement", config)
    response = await llm.ainvoke(
        {
            "input": analysis_prompt,
            "chat_history": get_chat_history(config),
        }
    )

    await adispatch_custom_event(
        "dataful-agent",
        {
            "content": "continue streaming",
        },
    )

    try:
        result = JsonOutputParser().parse(str(response.content))
        logger.debug(f"Execution decision: {result}")
        continue_execution = result.get("continue_execution", False)

        if continue_execution:
            return "next_sub_query"
        else:
            return "end_execution"
    except Exception as e:
        logger.error(f"Error parsing LLM response: {str(e)}")
        return "end_execution"
