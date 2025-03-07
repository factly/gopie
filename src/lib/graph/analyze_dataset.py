import json
from src.lib.graph.types import State
from langchain_core.output_parsers import JsonOutputParser

def analyze_dataset(state: State):
    """Analyze the dataset structure and prepare for query planning"""

    query_index = state.get("subquery_index", 0)
    user_query = state.get("subqueries")[query_index] if state.get("subqueries") else 'No input'

    parser = JsonOutputParser()

    last_message = state["messages"][-1].content
    parsed_content = parser.parse(last_message)

    print(json.dumps(parsed_content.get("column_requirements", "not found"), indent=2))

def route_from_dataset_analysis(state: State):
    """Route to the next node based on the results of dataset analysis"""
    return "plan_query"