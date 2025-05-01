from app.workflow.graph import graph


def visualize_graph():
    try:
        with open("graph/graph.png", "wb") as f:
            data = graph.get_graph().draw_mermaid_png()
            f.write(data)
            print("Data type:", type(data))
    except Exception as e:
        raise e
