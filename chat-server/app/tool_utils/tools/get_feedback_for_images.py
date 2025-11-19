from typing import Annotated

from e2b_code_interpreter import AsyncSandbox
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.utils.langsmith.prompt_manager import get_prompt_llm_chain
from app.workflow.graph.visualize_data_graph.types import Dataset
from app.workflow.graph.visualize_data_graph.utils import format_dataset_info


class IndividualFeedback(BaseModel):
    visualization_index: int = Field(description="Index of the visualization (1-based)")
    areas_for_improvement: str = Field(
        description="Brief, specific issues only (max 2-3 sentences). Leave empty if rating >= 7"
    )
    rating: float = Field(description="Rating from 1-10 for this visualization")


class MultiImageFeedback(BaseModel):
    individual_feedback: list[IndividualFeedback] = Field(
        description="Feedback for each individual visualization"
    )
    key_issues: str = Field(
        description="Only critical issues across visualizations (max 2-3 sentences). Leave empty if final_rating >= 7"
    )
    final_rating: float = Field(description="Overall rating from 1-10 for the complete set")


@tool
async def get_feedback_for_images(
    png_paths: list[str],
    dataset_paths: list[str],
    sandbox: Annotated[AsyncSandbox, InjectedState("sandbox")],
    feedback_count: Annotated[int, InjectedState("feedback_count")],
    user_query: Annotated[str, InjectedState("user_query")],
    datasets: Annotated[list[Dataset] | None, InjectedState("datasets")],
    tool_call_id: Annotated[str, InjectedToolCallId],
    config: RunnableConfig,
    status_message: str = "",
):
    """
    Analyzes multiple data visualization images to provide comprehensive feedback based on the dataset description and user query.

    This tool evaluates the visual design, data representation accuracy, query alignment, and best practices of multiple visualizations,
    as well as how well they work together as a cohesive set.

    Args:
        png_paths: A list of PNG file paths for the visualizations.
                 Example: ["viz1.png", "viz2.png"]
        dataset_paths: A list of paths to the datasets used in the visualizations.
        status_message: A short status message describing the action (<=120 chars).
    """
    if feedback_count < 2:
        selected_datasets = []
        if datasets:
            for dataset in datasets:
                if dataset.csv_path in dataset_paths:
                    selected_datasets.append(dataset)

        images = []
        for path in png_paths:
            image = await sandbox.files.read(path, format="bytes")
            images.append(image)

        chain = get_prompt_llm_chain("feedback", config, schema=MultiImageFeedback)

        response = await chain.ainvoke(
            {
                "images": images,
                "user_query": user_query,
                "dataset_description": format_dataset_info(datasets=selected_datasets),
            }
        )
    else:
        response = MultiImageFeedback(
            individual_feedback=[
                IndividualFeedback(
                    visualization_index=i + 1,
                    areas_for_improvement="",
                    rating=8.0,
                )
                for i in range(len(png_paths))
            ],
            key_issues="",
            final_rating=8.0,
        )

    low_rating_visualizations = [f for f in response.individual_feedback if f.rating < 7]
    feedback_text = "The visualizations are good. You can return the final result."

    if response.final_rating < 7 or low_rating_visualizations:
        feedback_text = ""

        if low_rating_visualizations:
            feedback_text += "Visualizations needing improvement:\n\n"
            viz_paths_to_fix = []

            for fb in low_rating_visualizations:
                viz_path = png_paths[fb.visualization_index - 1]
                viz_paths_to_fix.append(viz_path)

                feedback_text += (
                    f"• Viz {fb.visualization_index} ({viz_path}) - Rating: {fb.rating}/10\n"
                )
                if fb.areas_for_improvement:
                    feedback_text += f"  Issues: {fb.areas_for_improvement}\n"

            feedback_text += f"\nREGENERATE: {viz_paths_to_fix}\n\n"

        if response.key_issues:
            feedback_text += f"Key issues: {response.key_issues}\n\n"

        feedback_text += f"Overall rating: {response.final_rating}/10"

    state_update = {
        "feedback_count": feedback_count + 1,
        "messages": [
            ToolMessage(
                tool_call_id=tool_call_id,
                content=feedback_text,
            )
        ],
    }
    return Command(update=state_update)


def get_dynamic_tool_text(args: dict) -> str:
    png_paths = args.get("png_paths", {})
    return args.get("status_message") or f"Reviewing {len(png_paths)} visualizations"


__tool__ = get_feedback_for_images
__tool_category__ = "Data Visualization"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
