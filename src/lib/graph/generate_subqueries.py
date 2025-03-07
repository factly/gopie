import json
from src.lib.graph.types import State
from src.lib.config.langchain_config import lc
from langchain_core.output_parsers import JsonOutputParser
from src.lib.graph.types import IntermediateStep

def generate_subqueries(state: State):
  """Generate subqueries that would require separate SQL queries"""
  user_input = state['messages'][0].content if state['messages'] else ''

  prompt = f"""
      User Query: {user_input}

       Given a complex user query, generate the minimal number of essential sub-queries required to retrieve relevant information. Ensure that:

      - Given a complex user query, generate the minimum number of essential sub-queries required to retrieve relevant information. Follow these rules:
      - Ensure at least two sub-queries if the question involves multiple aspects. Avoid returning just one broad query unless it is truly sufficient.
      - Avoid redundancy—group related entities (like multiple locations, companies, or categories) into a single query.
      - Each sub-query must be distinct and cover a different aspect of the main query.
      - If no breakdown is required, return a refined version of the query in the list format.

      - Add subqueries in the list in such a way that first add queries which require data_analysis to the list and then the queries that will need information from the previous queries to answer the later query.

      RESPONSE FORMAT:
        {{
          "subqueries": ["subquery1", "subquery2"]
        }}
      (If no breakdown is required, return the refined user query in the list instead.)
    """

  response = lc.llm.invoke(prompt)

  parser = JsonOutputParser()
  parsed_content = parser.parse(str(response.content))

  return {
    "user_query": user_input,
    "subquery_index": -1,
    "subqueries": parsed_content.get("subqueries", [user_input]),
    "messages": [IntermediateStep.from_text(json.dumps(parsed_content, indent=2))]
  }