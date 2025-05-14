import json
import logging

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser

from app.core.langchain_config import lc
from app.workflow.graph.types import State


async def stream_updates(state: State) -> dict:
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    subquery_result = query_result.subqueries[query_index]
    reached_max_retries = subquery_result.retry_count >= 3

    if reached_max_retries:
        stream_update_prompt = f"""
        I need to create a brief update about a failed subquery for the user.

        Original User Query: "{query_result.original_user_query}"

        The system attempted to execute this subquery:
        "{subquery_result.query_text}"

        After {subquery_result.retry_count} attempts, the subquery
        could not be completed due to errors:
        {json.dumps(subquery_result.error_message)}

        SQL Query Used:
        {subquery_result.sql_query_used}

        Instructions:
        1. Explain in simple terms why the subquery failed
        2. Suggest a potential fix or alternative approach the user could try
        3. Mention whether we'll continue with other parts of the query or if
           this failure is critical
        4. Be professional but empathetic about the failure
        5. Keep your response concise (2-3 sentences)

        Your response should be informative, actionable, and user-friendly.
        """
    else:
        stream_update_prompt = f"""
        I need to create a brief update about a successfully executed subquery.

        Original User Query: "{query_result.original_user_query}"

        The system successfully executed this subquery {query_index + 1} /
        {len(query_result.subqueries)}:

        "{subquery_result.query_text}"

        Subquery Result:
        {json.dumps(subquery_result.to_dict())}

        Instructions:
        1. Briefly summarize what information was retrieved from this subquery
        2. Explain how this information relates to the user's original question
        3. Mention what the system will do next (if this is not the final
           subquery)
        4. Keep your response concise (2-3 sentences)

        Your response should be informative and forward-looking.
        """

    response = await lc.llm.ainvoke({"input": stream_update_prompt})

    logging.info(f"Stream updates response: {response.content}")

    return {"messages": [AIMessage(content=response.content)]}


async def check_further_execution_requirement(state: State) -> str:
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

    dependency_analysis_prompt = f"""
        I need to analyze whether further subqueries should be executed
        despite a failed subquery.

        Original User Query: "{query_result.original_user_query}"

        Failed Subquery ({query_index + 1}/{len(query_result.subqueries)}):
        "{current_subquery.query_text}"

        Error Message: {json.dumps(current_subquery.error_message)}

        SQL Query Used: {current_subquery.sql_query_used}

        Remaining Subqueries:
        {json.dumps([sq.query_text for sq in
                    query_result.subqueries[query_index+1:]])}

        Please analyze and determine:
        1. Is the failed subquery critical for the remaining subqueries to be
        meaningful?
        2. Do the remaining subqueries depend on the results of this failed
        subquery?
        3. Would continuing with the remaining subqueries still provide partial
        value to the user?

        Return only a single JSON object with this format:
        {{
            "continue_execution": true/false,
            "reasoning": "Brief explanation of your decision"
        }}
    """

    response = await lc.llm.ainvoke({"input": dependency_analysis_prompt})
    try:
        result = JsonOutputParser().parse(str(response.content))

        if result.get("continue_execution", False):
            return "next_sub_query"
        else:
            return "end_execution"
    except Exception:
        return "end_execution"
