import os

from langchain_core.runnables.graph import CurveStyle

from app.workflow.agent import agent_graph
from app.workflow.graph.multi_dataset_graph.graph import multi_dataset_graph
from app.workflow.graph.single_dataset_graph.graph import single_dataset_graph
from app.workflow.graph.visualize_data_graph.graph import (
    graph as visualize_data_graph,
)


def visualize_graph():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        graph_dir = os.path.join(current_dir, "..", "..", "workflow", "graph")

        generated_graphs_dir = os.path.join(graph_dir, "graph_mermaid")
        os.makedirs(generated_graphs_dir, exist_ok=True)

        with open(os.path.join(generated_graphs_dir, "multi_dataset_graph.mmd"), "w") as f:
            f.write(multi_dataset_graph.get_graph().draw_mermaid(curve_style=CurveStyle.BASIS))

        with open(os.path.join(generated_graphs_dir, "single_dataset_graph.mmd"), "w") as f:
            f.write(single_dataset_graph.get_graph().draw_mermaid(curve_style=CurveStyle.BASIS))

        with open(os.path.join(generated_graphs_dir, "visualize_data_graph.mmd"), "w") as f:
            f.write(visualize_data_graph.get_graph().draw_mermaid(curve_style=CurveStyle.BASIS))

        with open(os.path.join(generated_graphs_dir, "agent_graph.mmd"), "w") as f:
            f.write(agent_graph.get_graph().draw_mermaid(curve_style=CurveStyle.BASIS))

        print(f"Graph visualizations generated successfully: " f"{generated_graphs_dir}")

    except Exception as e:
        raise e
