import json
from src.lib.graph.types import State
from langchain_core.output_parsers import JsonOutputParser

def analyze_dataset(state: State) -> dict:
    """Analyze the dataset structure and prepare for query planning"""
    try:
        last_message = state["messages"][-1].content
        parsed_content = JsonOutputParser().parse(last_message)

        return {
            "column_requirements": parsed_content.get("column_requirements", []),
            "messages": state.get("messages", [])
        }
    except Exception as e:
        return {
            "error": f"Dataset analysis failed: {str(e)}",
            "messages": state.get("messages", [])
        }

def route_from_dataset_analysis(state: State) -> str:
    """Route to the next node based on analysis results"""
    return "plan_query"