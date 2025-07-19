from app.models.message import ErrorMessage
from app.utils.langsmith.prompt_manager import get_prompt
from app.workflow.events.event_utils import configure_node
from ...visualize_data_graph.types import State
from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks.manager import adispatch_custom_event


from app.workflow.graph.visualize_data_graph.utils import get_sandbox, update_sandbox_timeout, upload_csv_files

@configure_node(
    role="intermediate",
    progress_message="Preparing visualizations...",
)
async def pre_model_hook(state: State, config: RunnableConfig):
    """
    Prepares the environment and prompt messages for the data visualization agent before invoking the language model.

    If a sandbox already exists, its timeout is updated; otherwise, a new sandbox is created and CSV files from the datasets are uploaded. If input preparation has not yet occurred, a custom event is dispatched, prompt messages are generated using the user query and datasets, and the input is marked as prepared. Returns an updated state dictionary containing prompt messages and sandbox information. If a `ValueError` occurs, returns an error message.
    """
    messages = []
    output = {}
    existing_sandbox = state.get("sandbox")
    datasets = state["datasets"]
    result = state["result"]

    try:
        if existing_sandbox:
            await update_sandbox_timeout(existing_sandbox)
        else:
            sbx = await get_sandbox()
            output["sandbox"] = sbx
            csv_paths = await upload_csv_files(sbx, state["datasets"])
        if not state.get("is_input_prepared"):
            await adispatch_custom_event("gopie-agent", {"content": "Preparing visualization ..."})

            datasets_csv_info = ""
            for idx, (dataset, csv_path) in enumerate(zip(datasets, csv_paths)):
                datasets_csv_info += f"Dataset {idx + 1}: \n\n"
                datasets_csv_info += f"Description: {dataset.description}\n\n"
                datasets_csv_info += f"CSV Path: {csv_path}\n\n"

            messages = get_prompt(
                "visualize_data",
                user_query=state["user_query"],
                datasets_csv_info=datasets_csv_info,
            )

            output["is_input_prepared"] = True
        output["messages"] = messages
        return output
    except Exception as e:
        err_msg = f"Error while creating visualisations: {str(e)}"
        output["messages"] = [ErrorMessage(content=str(e))]

        result.errors.append(f"[ERROR] {err_msg}")

        return {
            "messages": [ErrorMessage(content=err_msg)],
            "sandbox": existing_sandbox,
            "is_input_prepared": state.get("is_input_prepared", False),
            "result": result,
        }