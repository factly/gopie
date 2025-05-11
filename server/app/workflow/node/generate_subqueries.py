from datetime import datetime

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser

from app.core.langchain_config import lc
from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import QueryResult
from app.workflow.graph.types import State


async def generate_subqueries(state: State):
    messages = state.get("messages", [])

    if messages and isinstance(messages[-1], HumanMessage):
        user_input = str(messages[-1].content)
    else:
        raise Exception("Last Message must be a user message")

    prompt = f"""
      User Query: {user_input}

      Analyze the user query and determine if it needs to be broken down into
      sub-queries or simply improved.

      Follow these guidelines:

      1. QUERY ASSESSMENT:
         - First, determine if the query can be handled in a single agent cycle
         - Consider complexity, number of distinct data operations, and
           interdependent steps

      2. DECISION CRITERIA:
         - ONLY break down the query if it's genuinely too complex for a
           single operation
         - If the query is straightforward or can be handled in one step,
           DO NOT break it down
         - Consider whether the query requires multiple distinct datasets or
           operations that depend on previous results

      3. BREAKDOWN RULES (ONLY if necessary):
         - Maximum 3 sub-queries allowed
         - Each sub-query should address a distinct aspect of the main question
         - Order sub-queries logically: place data retrieval/analysis queries
           first, followed by queries that depend on previous results
         - Make each sub-query clear, specific, and focused on a single task

      5. EXPLANATION:
         - Provide a very brief explanation (1-2 sentences) of what you did
           with the query
         - Explain whether you broke it down and why, or how you improved it
         - Keep it simple and client-friendly

      RESPONSE FORMAT:
      {{
        "needs_breakdown": true/false,
        "subqueries": ["subquery1", "subquery2", "subquery3"],
        "explanation": "Brief explanation of actions taken"
      }}

      IMPORTANT: Prioritize NOT breaking down queries unless absolutely
      necessary for successful execution.
    """

    response = await lc.llm.ainvoke({"input": prompt})

    query_result_object = QueryResult(
        original_user_query=user_input,
        timestamp=datetime.now(),
        execution_time=0,
        subqueries=[],
    )

    try:
        parser = JsonOutputParser()
        parsed_content = parser.parse(str(response.content))

        needs_breakdown = parsed_content.get("needs_breakdown", False)
        explanation = parsed_content.get("explanation", "")

        if needs_breakdown:
            subqueries = parsed_content.get("subqueries", [])
            if len(subqueries) > 3:
                subqueries = subqueries[:3]

            if not subqueries:
                subqueries = [user_input]
        else:
            subqueries = [user_input]

        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": explanation,
            },
        )

        return {
            "user_query": user_input,
            "subquery_index": -1,
            "subqueries": subqueries,
            "query_result": query_result_object,
            "messages": [
                IntermediateStep.from_json(
                    {
                        "needs_breakdown": needs_breakdown,
                        "subqueries": subqueries,
                        "original_query": user_input,
                    },
                )
            ],
        }
    except Exception as e:
        error_msg = f"Error parsing subqueries: {e!s}"
        default_subqueries = [user_input]

        return {
            "user_query": user_input,
            "subquery_index": -1,
            "subqueries": default_subqueries,
            "query_result": query_result_object,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }
