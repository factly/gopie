from app.workflow.graph import graph


def visualize_graph():
    try:
        with open("graph/graph.mmd", "w") as f:
            f.write(graph.get_graph().draw_mermaid())
    except Exception as e:
        raise e
