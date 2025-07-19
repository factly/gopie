from langgraph.graph import END, StateGraph

from app.models.schema import ConfigSchema
from app.tool_utils.tool_node import ModifiedToolNode as ToolNode
from app.tool_utils.tools import ToolNames
from .node.respond import respond
from .node.call_model import call_model, should_continue
from .node.pre_model_hook import pre_model_hook, should_continue_from_pre_model_hook
from .node.process_results import process_visualization_result
from .node.cleanup import cleanup_resources

from .types import State, InputState, OutputState

tool_names = [ToolNames.RUN_PYTHON_CODE, ToolNames.RESULT_PATHS]

workflow = StateGraph(
    state_schema=State,
    config_schema=ConfigSchema,
    input_schema=InputState,
    output_schema=OutputState,
)

workflow.add_node("pre_model_hook", pre_model_hook)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tool_names))
workflow.add_node("process_result", process_visualization_result)
workflow.add_node("cleanup", cleanup_resources)
workflow.add_node("respond", respond)

workflow.set_entry_point("pre_model_hook")

workflow.add_conditional_edges(
    "pre_model_hook",
    should_continue_from_pre_model_hook,
    {
        "agent": "agent",
        "cleanup": "cleanup",
    },
)

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "process_result": "process_result",
    },
)

workflow.add_edge("tools", "pre_model_hook")
workflow.add_edge("process_result", "cleanup")
workflow.add_edge("cleanup", "respond")
workflow.add_edge("respond", END)

graph = workflow.compile()
