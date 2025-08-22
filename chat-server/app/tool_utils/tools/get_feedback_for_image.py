import base64
from typing import Annotated

from e2b_code_interpreter import AsyncSandbox
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from pydantic import BaseModel

from app.utils.model_registry.model_provider import get_configured_llm_for_node
from app.workflow.graph.visualize_data_graph.types import Dataset
from app.workflow.graph.visualize_data_graph.utils import format_dataset_info

SYSTEM_PROMPT = """\
You are an expert data visualization analyst. Your task is to analyze a data visualization image and provide comprehensive feedback based on the dataset description and user query.

## Your Analysis Should Cover:

### 1. Visual Design & Clarity
- Assess the chart type appropriateness for the data and query and faithfullness to the user query
- Evaluate color choices, readability, and visual hierarchy
- Check for proper labeling of axes, legends, and titles
- Identify any visual clutter or missing elements
- are the labels overlapping each other
- are the labels legible and meaningful?

### 2. Data Representation Accuracy
- Verify if the visualization correctly represents the underlying data
- Check for appropriate scaling, proportions, and data ranges
- Identify any potential misrepresentations or distortions
- Assess completeness of data shown vs. dataset description

### 3. Query Alignment
- Determine how well the visualization answers the user's specific intent
- Identify if key insights relevant to the query are highlighted
- Check if the chart type and focus align with the user's intent
- Suggest alternative approaches if the current visualization misses the mark

### 4. Best Practices & Improvements
- Recommend specific improvements for better data storytelling
- Suggest alternative chart types if more appropriate only if the user query does not specify the visualization type
- Identify accessibility issues (color blindness, contrast, etc.)
- Propose enhancements for better user understanding

## Response Fields:
Provide your feedback in a structured format:
1. Overall Assessment: Brief summary of visualization effectiveness and justification for the assessment and rating
2. Strengths: What works well in the current visualization
3. Areas for Improvement: Specific issues and recommendations
4. Alternative Suggestions: If the user query does not specify any specific visualization type then suggest a visualization type, else suggest improvements to the current visualization
5. Final Rating: Score from 1-10


Response Format:
{
    "overall_assessment": str,
    "strengths": str,
    "areas_for_improvement": str,
    "alternative_suggestions": str,
    "final_rating": float
}

Be constructive, specific, and actionable in your feedback. Focus on helping improve the visualization's ability to communicate insights effectively.
"""

USER_PROMPT = """\
User Query:
{user_query}
Datasets Description
{dataset_description}
"""

# Define prompt
prompt = ChatPromptTemplate(
    [
        SystemMessage(content=SYSTEM_PROMPT),
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source_type": "base64",
                    "data": "{image_data}",
                    "mime_type": "image/png",
                },
                {"type": "text", "text": USER_PROMPT},
            ],
        },
    ]
)


def image_to_base64(image: bytearray) -> str:
    return base64.b64encode(image).decode("utf-8")


class Feedback(BaseModel):
    overall_assessment: str
    strengths: str
    areas_for_improvement: str
    alternative_suggestions: str
    final_rating: float


@tool
async def get_feedback_for_image(
    png_path: str,
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
    Analyzes a data visualization image to provide comprehensive feedback based on the dataset description and user query.

    This tool evaluates the visual design, data representation accuracy, query alignment, and best practices of the visualization.
    """
    if feedback_count < 2:
        # Fetch datasets from state using dataset_paths
        selected_datasets = []
        if datasets:
            for dataset in datasets:
                if dataset.csv_path in dataset_paths:
                    selected_datasets.append(dataset)
        
        llm = get_configured_llm_for_node("visualize_data", config, schema=Feedback)
        image = await sandbox.files.read(png_path, format="bytes")
        prompt_value = prompt.invoke(
            {
                "image_data": image_to_base64(image),
                "dataset_description": format_dataset_info(datasets=selected_datasets),
                "user_query": user_query,
            }
        )
        response = await llm.ainvoke(prompt_value.to_messages())
    else:
        response = Feedback(
            overall_assessment="",
            strengths="",
            areas_for_improvement="",
            alternative_suggestions="",
            final_rating=8,
        )

    feedback_text = "The visualization is good. You can return the final result."
    if response.final_rating < 7:
        feedback_text = ""
        if response.overall_assessment:
            feedback_text += f"Overall Assessment:\n\n{response.overall_assessment}\n\n"
        if response.strengths:
            feedback_text += f"Strengths:\n\n{response.strengths}\n\n"
        if response.areas_for_improvement:
            feedback_text += f"Areas for Improvement\n\n{response.areas_for_improvement}\n\n"
        if response.alternative_suggestions:
            feedback_text += f"Alternative Suggestions\n\n{response.alternative_suggestions}\n\n"
        feedback_text += f"Final Rating: {response.final_rating}/10"

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
    return args.get("status_message") or "Reviewing the generated Visualization"


__tool__ = get_feedback_for_image
__tool_category__ = "Data Visualization"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
