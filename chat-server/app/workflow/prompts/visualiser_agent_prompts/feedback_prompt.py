import base64

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate


def create_feedback_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")
    image_data_list = kwargs.get("image_data_list", [])

    system_content = """\
You are an expert data visualization analyst. Analyze the visualizations and provide CONCISE, focused feedback.

## Rating Scale:
- 8-10: Visualization is correct, clear, and matches the user's query. No changes needed.
- 7: Minor cosmetic issues but functionally correct and readable.
- 4-6: Has meaningful issues affecting clarity, correctness, or query alignment.
- 1-3: Fundamentally broken or misleading.

## IMPORTANT: If a visualization correctly represents the data and answers the user's query with readable labels and appropriate chart type, rate it 7 or above. Do NOT penalize for minor aesthetic preferences.

## Evaluation Criteria (check for ACTUAL problems only):
1. **Chart Type & Query Alignment**: Does it match the user's request and data type?
2. **Visual Clarity**: Are labels readable, non-overlapping, and properly sized?
3. **Data Accuracy**: Correct scaling, no distortions, complete data representation
4. **Technical Issues**: Negative values where inappropriate, cut-off labels, wrong chart types

## Guidelines:
- Only flag issues that are genuinely wrong or broken — not stylistic preferences
- Be specific and actionable (e.g., "Rotate x-axis labels 45° to prevent overlap")
- If rating >= 7, you MUST leave areas_for_improvement as an empty string and key_issues as an empty string
- Avoid generic comments about "consistency" or "styling" unless they cause real readability issues
- Keep each feedback point to 1-2 sentences maximum

## Response Requirements:
- **Individual Feedback**: For each visualization with rating < 7, list specific fixable issues only. For rating >= 7, areas_for_improvement MUST be empty string.
- **Key Issues**: Only mention critical problems affecting multiple visualizations. MUST be empty string if final_rating >= 7.
- **Ratings**: Rate based on functional correctness and clarity. A correct, readable visualization that answers the query is a 7+.

Do NOT invent problems when the visualization is correct.
"""

    if prompt_template:
        from langchain_core.prompts import MessagesPlaceholder

        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                MessagesPlaceholder(variable_name="image_messages"),
            ]
        )

    content_parts = []

    for idx, image_data in enumerate(image_data_list):
        content_parts.append(
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
        )
        content_parts.append({"type": "text", "text": f"\n--- Visualization {idx + 1} ---\n"})

    content_parts.append({"type": "text", "text": input_content})

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=content_parts),
    ]


def format_feedback_input(
    images: list[bytearray],
    user_query: str,
    dataset_description: str,
) -> dict:
    """
    Build the content parts for the feedback prompt with multiple images.

    Args:
        images: List of image byte arrays
        user_query: The user's query
        dataset_description: Formatted dataset description

    Returns:
        Dict with properly formatted input for the feedback prompt
    """

    def image_to_base64(image: bytearray) -> str:
        return base64.b64encode(image).decode("utf-8")

    user_prompt_text = f"""\
User Query: {user_query}

Dataset Info: {dataset_description}

Analyze {len(images)} visualization(s) above. Provide ratings and list ONLY critical issues that need fixing.
"""

    content_parts = []

    for idx, image in enumerate(images):
        image_b64 = image_to_base64(image)
        content_parts.append(
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
        )
        content_parts.append({"type": "text", "text": f"\n--- Visualization {idx + 1} ---\n"})

    content_parts.append({"type": "text", "text": user_prompt_text})
    image_messages = [HumanMessage(content=content_parts)]

    return {
        "image_messages": image_messages,
    }
