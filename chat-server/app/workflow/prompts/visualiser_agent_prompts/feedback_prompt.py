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

## Evaluation Criteria:
1. **Chart Type & Query Alignment**: Does it match the user's request and data type?
2. **Visual Clarity**: Are labels readable, non-overlapping, and properly sized?
3. **Data Accuracy**: Correct scaling, no distortions, complete data representation
4. **Technical Issues**: Negative values where inappropriate, cut-off labels, wrong chart types

## Guidelines:
- Focus ONLY on critical issues that need fixing
- Be specific and actionable (e.g., "Rotate x-axis labels 45° to prevent overlap")
- If rating >= 7, leave improvement fields EMPTY
- Avoid generic comments about "consistency" or "styling" unless specific
- Don't list strengths - only problems that need attention
- Keep each feedback point to 1-2 sentences maximum

## Response Requirements:
- **Individual Feedback**: For each visualization with rating < 7, list specific fixable issues only
- **Key Issues**: Only mention critical problems affecting multiple visualizations (max 2-3 sentences)
- **Ratings**: Rate honestly based on functionality, not aesthetics

Be direct, brief, and focus on actionable improvements only.
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
