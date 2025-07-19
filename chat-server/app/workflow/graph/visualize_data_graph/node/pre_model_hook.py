from app.models.message import ErrorMessage
from app.utils.langsmith.prompt_manager import get_prompt
from ...visualize_data_graph.types import AgentState
from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks.manager import adispatch_custom_event


from app.workflow.graph.visualize_data_graph.utils import get_sandbox, update_sandbox_timeout, upload_csv_files

async def pre_model_hook(state: AgentState, config: RunnableConfig):
    """
    Prepares the environment and prompt messages for the data visualization agent before invoking the language model.

    If a sandbox already exists, its timeout is updated; otherwise, a new sandbox is created and CSV files from the datasets are uploaded. If input preparation has not yet occurred, a custom event is dispatched, prompt messages are generated using the user query and datasets, and the input is marked as prepared. Returns an updated state dictionary containing prompt messages and sandbox information. If a `ValueError` occurs, returns an error message.
    """
    messages = []
    output = {}
    existing_sandbox = state.get("sandbox")
    try:
        if existing_sandbox:
            await update_sandbox_timeout(existing_sandbox)
        else:
            sbx = await get_sandbox()
            output["sandbox"] = sbx
            csv_paths = await upload_csv_files(sbx, state["datasets"])
        if not state.get("is_input_prepared"):
            await adispatch_custom_event("gopie-agent", {"content": "Preparing visualization ..."})

            messages = get_prompt(
                "visualize_data",
                user_query=state["user_query"],
                datasets=state["datasets"],
                csv_paths=csv_paths,
            )

            output["is_input_prepared"] = True
        output["messages"] = messages
        return output
    except ValueError as e:
        return {"messages": [ErrorMessage(content=str(e))]}