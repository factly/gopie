import os

from langchain_core.runnables.graph import CurveStyle

from app.workflow.graph.multi_dataset_graph import multi_dataset_graph


def visualize_graph():
    try:
        os.makedirs("graph", exist_ok=True)
        with open("graph/graph.mmd", "w") as f:
            f.write(
                multi_dataset_graph.get_graph().draw_mermaid(
                    curve_style=CurveStyle.BASIS
                )
            )
    except Exception as e:
        raise e
