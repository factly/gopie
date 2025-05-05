import os

from langchain_core.runnables.graph import CurveStyle

from app.workflow.graph import graph


def visualize_graph():
    try:
        os.makedirs("graph", exist_ok=True)

        with open("graph/graph.png", "wb") as f:
            data = graph.get_graph().draw_mermaid_png(
                curve_style=CurveStyle.BASIS
            )
            data = data.replace(
                b"graph TD",
                b"graph TD\n  %%{ init: {'flowchart': {'curve': 'basis'}} }%%",
            )
            f.write(data)
    except Exception as e:
        raise e
