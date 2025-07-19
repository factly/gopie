from langgraph.graph import END, StateGraph

from app.models.schema import ConfigSchema
from app.tool_utils.tool_node import ModifiedToolNode as ToolNode
from app.tool_utils.tools import ToolNames
from .node.call_model import call_model, should_continue
from .node.pre_model_hook import pre_model_hook
from .node.visualization_response import respond

from .types import AgentState, InputState, OutputState

tool_names = [ToolNames.RUN_PYTHON_CODE, ToolNames.RESULT_PATHS]

workflow = StateGraph(
    state_schema=AgentState,
    config_schema=ConfigSchema,
    input_schema=InputState,
    output_schema=OutputState,
)
workflow.add_node("agent", call_model)
workflow.add_node("pre_model_hook", pre_model_hook)
workflow.add_node("respond", respond)
workflow.add_node("tools", ToolNode(tool_names))

workflow.set_entry_point("pre_model_hook")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "respond": "respond",
    },
)

workflow.add_edge("tools", "pre_model_hook")
workflow.add_edge("pre_model_hook", "agent")
workflow.add_edge("respond", END)
graph = workflow.compile()
