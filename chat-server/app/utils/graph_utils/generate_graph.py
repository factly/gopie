import os

from langchain_core.runnables.graph import CurveStyle

from app.workflow.graph.multi_dataset_graph import multi_dataset_graph
from app.workflow.graph.single_dataset_graph import simple_graph
from app.workflow.graph.visualize_data_graph import visualize_data_graph


def visualize_graph():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        graph_dir = os.path.join(current_dir, "..", "..", "workflow", "graph")

        os.makedirs(
            os.path.join(graph_dir, "multi_dataset_graph"), exist_ok=True
        )
        os.makedirs(
            os.path.join(graph_dir, "single_dataset_graph"), exist_ok=True
        )
        os.makedirs(
            os.path.join(graph_dir, "visualize_data_graph"), exist_ok=True
        )

        with open(
            os.path.join(graph_dir, "multi_dataset_graph", "graph.mmd"), "w"
        ) as f:
            f.write(
                multi_dataset_graph.get_graph().draw_mermaid(
                    curve_style=CurveStyle.BASIS
                )
            )

        with open(
            os.path.join(graph_dir, "single_dataset_graph", "graph.mmd"), "w"
        ) as f:
            f.write(
                simple_graph.get_graph().draw_mermaid(
                    curve_style=CurveStyle.BASIS
                )
            )

        with open(
            os.path.join(graph_dir, "visualize_data_graph", "graph.mmd"), "w"
        ) as f:
            f.write(
                visualize_data_graph.get_graph().draw_mermaid(
                    curve_style=CurveStyle.BASIS
                )
            )

        print("Graph visualizations generated successfully:")
        print(
            f"- Multi-dataset graph: {graph_dir}/multi_dataset_graph/graph.mmd"  # noqa: E501
        )
        print(
            f"- Single-dataset graph: {graph_dir}/single_dataset_graph/graph.mmd"  # noqa: E501
        )
        print(
            f"- Visualize data graph: {graph_dir}/visualize_data_graph/graph.mmd"  # noqa: E501
        )

    except Exception as e:
        raise e
