from langgraph.graph import END, START, StateGraph

from app.workflow.agent.supervisor.initial_sup import route_initial_supervisor
from app.workflow.agent.supervisor.virtualizer_sup import (
    route_visualization_supervisor,
)
from app.workflow.agent.types import ConfigSchema, State
from app.workflow.graph.multi_dataset_graph import call_multidataset_graph
from app.workflow.graph.single_dataset_graph import call_single_dataset_graph
from app.workflow.graph.visualize_data_graph import call_visualize_data_graph

graph_builder = StateGraph(State, config_schema=ConfigSchema)


graph_builder.add_node("supervisor", route_initial_supervisor)
graph_builder.add_node("multidataset_agent", call_multidataset_graph)
graph_builder.add_node("single_dataset_agent", call_single_dataset_graph)
graph_builder.add_node("visualizer_agent", call_visualize_data_graph)
graph_builder.add_node(
    "visualization_supervisor", route_visualization_supervisor
)

graph_builder.add_conditional_edges(
    "supervisor",
    route_initial_supervisor,
    {
        "multidataset_agent": "multidataset_agent",
        "single_dataset_agent": "single_dataset_agent",
    },
)

graph_builder.add_conditional_edges(
    "visualization_supervisor",
    route_visualization_supervisor,
    {
        "visualizer_agent": "visualizer_agent",
        "__end__": END,
    },
)

graph_builder.add_edge(START, "supervisor")
graph_builder.add_edge("multidataset_agent", "visualization_supervisor")
graph_builder.add_edge("single_dataset_agent", "visualization_supervisor")
graph_builder.add_edge("visualizer_agent", END)

agent_graph = graph_builder.compile()
