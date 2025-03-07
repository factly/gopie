from src.lib.graph.types import State
from src.lib.config.langchain_config import lc
from langchain_core.output_parsers import JsonOutputParser

def generate_subqueries(state: State):
  """Generate subqueries of the user input query"""

  user_query = state.get("user_query", "")

  prompt = f"""
    Given the user query: {user_query}
    Analyze if the query requires breaking down into smaller subqueries. Only generate subqueries if:
    1. The query asks for multiple distinct pieces of information that would require separate SQL queries
    2. The query is complex and would be difficult to answer with a single SQL query
    3. The query has multiple conditions or comparisons across different aspects of data

    If subqueries are not needed, respond with an empty array.

    RESPONSE FORMAT:
      Respond in this JSON format:
      {
        "subqueries": ["subquery1", "subquery2"]
      }

      Examples:
      "Show me total sales" -> {"subqueries": []} // Simple query, no breakdown needed
      "Compare sales in 2022 vs 2021 and show top products in each year" ->
        {"subqueries": ["Get sales for 2022", "Get sales for 2021", "Get top products for 2022", "Get top products for 2021"]}
    """

  response = lc.llm.invoke(prompt)

  parser = JsonOutputParser()
  parsed_content = parser.parse(str(response.content))

  return {
    "subqueries": parsed_content.get("subqueries", [user_query]),
  }