import base64
from typing import Annotated

from e2b_code_interpreter import AsyncSandbox
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState

from app.utils.model_registry.model_provider import get_configured_llm_for_node
from app.workflow.graph.visualize_data_graph.types import Dataset
from app.workflow.graph.visualize_data_graph.utils import format_dataset_info

SYSTEM_PROMPT = """\
You are an expert data visualization analyst. Your task is to analyze a data visualization image and provide comprehensive feedback based on the dataset description and user query.

## Your Analysis Should Cover:

### 1. Visual Design & Clarity
- Assess the chart type appropriateness for the data and query
- Evaluate color choices, readability, and visual hierarchy
- Check for proper labeling of axes, legends, and titles
- Identify any visual clutter or missing elements

### 2. Data Representation Accuracy
- Verify if the visualization correctly represents the underlying data
- Check for appropriate scaling, proportions, and data ranges
- Identify any potential misrepresentations or distortions
- Assess completeness of data shown vs. dataset description

### 3. Query Alignment
- Determine how well the visualization answers the user's specific question
- Identify if key insights relevant to the query are highlighted
- Check if the chart type and focus align with the user's intent
- Suggest alternative approaches if the current visualization misses the mark

### 4. Best Practices & Improvements
- Recommend specific improvements for better data storytelling
- Suggest alternative chart types if more appropriate
- Identify accessibility issues (color blindness, contrast, etc.)
- Propose enhancements for better user understanding

## Response Format:
Provide your feedback in a structured format:
1. **Overall Assessment**: Brief summary of visualization effectiveness
2. **Strengths**: What works well in the current visualization
3. **Areas for Improvement**: Specific issues and recommendations
4. **Alternative Suggestions**: If applicable, suggest different approaches
5. **Final Rating**: Score from 1-10 with brief justification

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
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
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


@tool
async def get_feedback_for_image(
    png_path: str,
    datasets: list[Dataset],
    sandbox: Annotated[AsyncSandbox, InjectedState("sandbox")],
    user_query: Annotated[str, InjectedState("user_query")],
    tool_call_id: Annotated[str, InjectedToolCallId],
    config: RunnableConfig,
):
    """\
    Analyzes a data visualization image to provide comprehensive feedback based on the dataset description and user query.

    This tool evaluates the visual design, data representation accuracy, query alignment, and best practices of the visualization.
    """
    llm = get_configured_llm_for_node("visualize_data", config)
    chain = prompt | llm | StrOutputParser()
    image = await sandbox.files.read(png_path, format="bytes")
    response = await chain.ainvoke(
        {
            "image_data": image_to_base64(image),
            "dataset_description": format_dataset_info(datasets),
            "user_query": user_query,
        }
    )
    return response


def get_dynamic_tool_text(args: dict) -> str:
    return "Reviewing the generated Visualization"


__tool__ = get_feedback_for_image
__tool_category__ = "Data Visualization"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
