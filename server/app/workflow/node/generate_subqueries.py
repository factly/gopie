import json
from datetime import datetime

from langchain_core.output_parsers import JsonOutputParser

from server.app.core.langchain_config import lc
from server.app.models.types import ErrorMessage, IntermediateStep, QueryResult
from server.app.workflow.graph.types import State


async def generate_subqueries(state: State):
    """Generate subqueries that would require separate SQL queries"""
    messages = state.get("messages", [])
    user_input = messages[0].content if messages else ""

    prompt = f"""
      User Query: {user_input}

      Analyze the user query and divide it into logical sub-steps if necessary. Follow these guidelines:

      - Break down complex queries that would be difficult to handle in a single SQL query
      - Only create sub-queries when they're genuinely needed (for different data aspects or computational steps)
      - If the query is simple enough to handle with one SQL query, return an empty list
      - Order sub-queries logically: place data retrieval/analysis queries first, followed by queries that depend on previous results
      - Focus only on the specific entities mentioned in the query (e.g., only the specified districts, not all districts)
      - Ensure each sub-query addresses a distinct aspect of the main question

      For example, for a query like "Is it a fact that no CSR funds were spent in the five backward districts of Telangana?",
      you could divide it into this sub-query:
      "Check if the specified backward districts of Telangana (Jagtial, Peddapalli, Jayashankar Bhupalpally, Nagarkurnool and Jogulamba) have zero CSR funds"

      CAUTION: Do not write subqueries that would retrieve the whole tuples of the tables or process entities not explicitly mentioned in the query.
      Instead, write subqueries that would retrieve only the required values for the specific entities mentioned.

      RESPONSE FORMAT:
      {{
        "subqueries": ["subquery1", "subquery2"]
      }}

      (Return an empty list if the query doesn't need to be divided)
    """

    response = await lc.llm.ainvoke(prompt)

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

        subqueries = None
        print(parsed_content.get("subqueries"))

        if not subqueries:
            subqueries = [user_input]

        return {
            "user_query": user_input,
            "subquery_index": -1,
            "subqueries": subqueries,
            "query_result": query_result_object,
            "messages": [
                IntermediateStep.from_text(json.dumps(parsed_content, indent=2))
            ],
        }
    except Exception as e:
        query_result_object.add_error_message(
            str(e), "Error parsing subqueries in generate_subqueries"
        )
        error_msg = f"Error parsing subqueries: {str(e)}"

        return {
            "user_query": user_input,
            "query_result": query_result_object,
            "messages": [
                ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))
            ],
        }
