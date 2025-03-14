import json
from datetime import datetime

from langchain_core.output_parsers import JsonOutputParser

from src.lib.config.langchain_config import lc
from src.lib.graph.query_result.query_type import QueryResult
from src.lib.graph.types import ErrorMessage, IntermediateStep, State


def generate_subqueries(state: State):
    """Generate subqueries that would require separate SQL queries"""
    user_input = state["messages"][0].content if state["messages"] else ""

    prompt = f"""
      User Query: {user_input}

      Analyze the user query and divide it into logical sub-steps if necessary. Follow these guidelines:

      - Break down complex queries that would be difficult to handle in a single SQL query
      - Only create sub-queries when they're genuinely needed (for different data aspects or computational steps)
      - If the query is simple enough to handle with one SQL query, return an empty list
      - Order sub-queries logically: place data retrieval/analysis queries first, followed by queries that depend on previous results
      - Avoid redundancy by grouping related entities (locations, companies, categories) in the same sub-query
      - Ensure each sub-query addresses a distinct aspect of the main question

      RESPONSE FORMAT:
      {{
        "subqueries": ["subquery1", "subquery2"]
      }}

      (Return an empty list if the query doesn't need to be divided)
    """

    response = lc.llm.invoke(prompt)
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

        subqueries = parsed_content.get("subqueries")

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
            "query_result": query_result_object,
            "messages": [
                ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))
            ],
        }
