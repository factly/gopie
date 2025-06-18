from langgraph.graph import END, StateGraph

from app.models.schema import ConfigSchema
from app.workflow.agent.supervisor import dummy_supervisor, supervisor
from app.workflow.agent.types import State
from app.workflow.graph.multi_dataset_graph import multi_dataset_graph
from app.workflow.graph.single_dataset_graph import single_dataset_graph
from app.workflow.graph.visualize_data_graph import visualize_data_graph

graph_builder = StateGraph(State, config_schema=ConfigSchema)


graph_builder.add_node(
    supervisor,
    destinations=("multi_dataset_agent", "single_dataset_agent"),
)
graph_builder.add_node("multi_dataset_agent", multi_dataset_graph)
graph_builder.add_node("single_dataset_agent", single_dataset_graph)
graph_builder.add_node("visualizer_agent", visualize_data_graph)

# NOTE: This is just for sake of visualization of graph.
graph_builder.add_node(
    dummy_supervisor, destinations=("visualizer_agent", END)
)

graph_builder.set_entry_point("supervisor")
graph_builder.add_edge("multi_dataset_agent", "dummy_supervisor")
graph_builder.add_edge("single_dataset_agent", "dummy_supervisor")
graph_builder.add_edge("visualizer_agent", END)

agent_graph = graph_builder.compile()
