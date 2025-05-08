from datetime import datetime

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

      4. QUERY IMPROVEMENT (if no breakdown needed):
         - If the original query is unclear or ambiguous but doesn't need
           breaking down, provide an improved version
         - Clarify ambiguous terms, specify entities more precisely, or
           reword for clarity
         - If the original query is already clear and specific, return it
           unchanged

      RESPONSE FORMAT:
      {{
        "needs_breakdown": true/false,
        "subqueries": ["subquery1", "subquery2", "subquery3"],
        "improved_query": "improved version of original query if no breakdown
                           needed"
      }}

      IMPORTANT: Prioritize NOT breaking down queries unless absolutely
      necessary for successful execution.
    """

    response = await lc.llm.ainvoke({"input": prompt})

    query_result_object = QueryResult(
        original_user_query=user_input,
        timestamp=datetime.now(),
        error_message=None,
        execution_time=0,
        subqueries=[],
    )

    try:
        parser = JsonOutputParser()
        parsed_content = parser.parse(str(response.content))

        needs_breakdown = parsed_content.get("needs_breakdown", False)

        if needs_breakdown:
            subqueries = parsed_content.get("subqueries", [])
            if len(subqueries) > 3:
                subqueries = subqueries[:3]

            if not subqueries:
                subqueries = [user_input]
        else:
            improved_query = parsed_content.get("improved_query", user_input)
            subqueries = [improved_query]

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
        query_result_object.add_error_message(
            str(e), "Error parsing subqueries in generate_subqueries"
        )
        error_msg = f"Error parsing subqueries: {e!s}"

        default_subqueries = [user_input]

        return {
            "user_query": user_input,
            "subquery_index": -1,
            "subqueries": default_subqueries,
            "query_result": query_result_object,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }
