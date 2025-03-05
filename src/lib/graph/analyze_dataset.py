from src.lib.graph.types import State
from langchain_core.messages import AIMessage

def analyze_dataset(state: State):
    """Analyze the dataset structure and prepare for query planning"""

    return {
        "current_node": "analyze_dataset",
        **state
    }
