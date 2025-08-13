from langgraph.graph import END, StateGraph

from app.models.schema import ConfigSchema
from app.tool_utils.tool_node import ModifiedToolNode as ToolNode
from app.tool_utils.tools import ToolNames
from app.workflow.graph.visualize_data_graph.node.pre_process_data import (
    pre_process_visualization_data,
)

from .node.call_model import call_model, should_continue
from .node.cleanup import cleanup_resources
from .node.pre_model_hook import (
    pre_model_hook,
    should_continue_from_pre_model_hook,
)
from .node.process_results import process_visualization_result
from .node.respond import respond
from .types import InputState, OutputState, State

tool_names = [ToolNames.RUN_PYTHON_CODE, ToolNames.RESULT_PATHS, ToolNames.GET_FEEDBACK_FOR_IMAGE]

workflow = StateGraph(
    state_schema=State,
    config_schema=ConfigSchema,
    input_schema=InputState,
    output_schema=OutputState,
)

workflow.add_node("pre_process_data", pre_process_visualization_data)
workflow.add_node("pre_model_hook", pre_model_hook)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tool_names))
workflow.add_node("process_result", process_visualization_result)
workflow.add_node("cleanup", cleanup_resources)
workflow.add_node(should_continue, 
                destinations=("tools", "process_result", "agent"))
workflow.add_node("respond", respond)

workflow.set_entry_point("pre_process_data")

workflow.add_conditional_edges(
    "pre_model_hook",
    should_continue_from_pre_model_hook,
    {
        "agent": "agent",
        "cleanup": "cleanup",
    },
)

workflow.add_edge("agent", "should_continue")

workflow.add_edge("pre_process_data", "pre_model_hook")
workflow.add_edge("tools", "pre_model_hook")
workflow.add_edge("process_result", "cleanup")
workflow.add_edge("cleanup", "respond")
workflow.add_edge("respond", END)

graph = workflow.compile()
