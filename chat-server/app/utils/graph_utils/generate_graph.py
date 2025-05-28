import os
from langchain_core.runnables.graph import CurveStyle

from app.workflow.graph import graph


def visualize_graph():
    try:
        os.makedirs("graph", exist_ok=True)
        with open("graph/graph.mmd", "w") as f:
            f.write(
                graph.get_graph().draw_mermaid(curve_style=CurveStyle.BASIS)
            )
    except Exception as e:
        raise e
