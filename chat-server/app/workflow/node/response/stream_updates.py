import json
import logging

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.types import State


async def stream_updates(state: State, config: RunnableConfig) -> dict:
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    subquery_result = query_result.subqueries[query_index]
    reached_max_retries = subquery_result.retry_count >= 3
    sql_queries = [
        sql_info.sql_query for sql_info in subquery_result.sql_queries
    ]

    if reached_max_retries:
        stream_update_prompt = f"""
        I need to create a brief update about a failed subquery for the user.

        Original User Query: "{query_result.original_user_query}"

        The system attempted to execute this subquery:
        "{subquery_result.query_text}"

        After {subquery_result.retry_count} attempts, the subquery
        could not be completed due to errors:
        {json.dumps(subquery_result.error_message)}

        SQL Queries Used:
        {json.dumps(sql_queries, indent=2)}

        Remaining Subqueries:
        {json.dumps([sq.query_text for sq in
                    query_result.subqueries[query_index + 1:]])}

        First, analyze dependencies:
        1. Is this failed subquery critical for the remaining subqueries?
        2. Do the remaining subqueries depend on the results of this failed
           subquery?
        3. Would continuing with the remaining subqueries still provide value?

        Then create a user-friendly update that:
        1. Explains in simple terms why the subquery failed
        2. Suggests a potential fix or alternative approach
        3. Clearly states whether you'll continue with other parts of the query
           or if this failure is critical and we need to stop
        4. Is professional but empathetic about the failure
        5. Keeps the response concise (2-3 sentences)

        Your update should be informative, actionable, and user-friendly.
        IMPORTANT: Be explicit about whether execution will continue or stop.
        """
    else:
        stream_update_prompt = f"""
        I need to create a brief update about a successfully executed subquery.

        Original User Query: "{query_result.original_user_query}"

        The system successfully executed this subquery {query_index + 1} /
        {len(query_result.subqueries)}:

        "{subquery_result.query_text}"

        SQL Queries Information:
        {json.dumps(sql_queries, indent=2)}

        Subquery Result Information:
        {json.dumps(subquery_result.to_dict())}

        Instructions:
        1. Briefly summarize what information was retrieved from this subquery
        2. Explain how this information relates to the user's original question
        3. Mention which SQL queries were executed and if any had large results
           that were summarized
        4. Mention what the system will do next (if this is not the final
           subquery)
        5. Keep your response concise (2-3 sentences)

        Your response should be informative and forward-looking.
        """

    llm = get_llm_for_node("stream_updates", config)
    response = await llm.ainvoke(
        {
            "input": stream_update_prompt,
            "chat_history": get_chat_history(config),
        }
    )

    logging.debug(f"Stream updates response: {response.content}")

    return {"messages": [AIMessage(content=response.content)]}


async def check_further_execution_requirement(
    state: State, config: RunnableConfig
) -> str:
    """
    Determines if further execution is required based on the current state.
    Returns a string indicating the next step: "next_sub_query" or
    "end_execution".
    """
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    current_subquery = query_result.subqueries[query_index]
    reached_max_retries = current_subquery.retry_count >= 3

    if not reached_max_retries:
        return "next_sub_query"

    await adispatch_custom_event(
        "dataful-agent",
        {
            "content": "do not stream",
        },
    )

    last_stream_message = state.get("messages", [])[-1]

    sql_queries = [
        sql_info.sql_query for sql_info in current_subquery.sql_queries
    ]

    dependency_analysis_prompt = f"""
        I need to analyze whether further subqueries should be executed
        despite a failed subquery.

        Original User Query: "{query_result.original_user_query}"
        Last Stream Message: "{last_stream_message.content}"

        Failed Subquery ({query_index + 1}/{len(query_result.subqueries)}):
        "{current_subquery.query_text}"

        Error Message: {json.dumps(current_subquery.error_message)}

        SQL Queries Used: {json.dumps(sql_queries)}

        Remaining Subqueries:
        {json.dumps([sq.query_text for sq in
                    query_result.subqueries[query_index + 1:]])}

        The last stream message likely contains a decision about whether
        to continue execution. First, analyze this message to see if it
        explicitly states a decision.

        Then analyze these factors:
        1. Is the failed subquery critical for the remaining subqueries to be
        meaningful?
        2. Do the remaining subqueries depend on the results of this failed
        subquery?
        3. Would continuing with the remaining subqueries still provide partial
        value to the user?

        If the last message clearly indicates a decision about continuing or
        stopping, that should heavily influence your decision.

        Return only a single JSON object with this format:
        {{
            "continue_execution": boolean (true or false, not a string),
            "reasoning": "Brief explanation of your decision"
        }}

        IMPORTANT: The "continue_execution" value MUST be a boolean
        (true/false), not a string. Do not wrap it in quotes.
    """

    llm = get_llm_for_node("check_further_execution_requirement", config)
    response = await llm.ainvoke(
        {
            "input": dependency_analysis_prompt,
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

        logging.debug(f"Result: {result}")

        continue_execution = result.get("continue_execution", False)

        if continue_execution:
            return "next_sub_query"
        else:
            return "end_execution"
    except Exception as e:
        logging.error(f"Error parsing LLM response: {str(e)}")
        return "end_execution"
