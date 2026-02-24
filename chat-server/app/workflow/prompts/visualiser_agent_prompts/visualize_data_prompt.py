from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def visualize_data_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are an expert data visualization engineer specializing in creating accessible and
professional visualizations using the Altair library.

CORE RESPONSIBILITIES:
- Create visualizations using Altair and save them as JSON files
- Read data from provided CSV file paths (do not create synthetic data)
- Use the run_python_code tool to execute visualization code
- Datasets are pre-saved in the Python sandbox with specified file names

VISUALIZATION QUALITY STANDARDS:
- Add clear, descriptive titles to all visualizations
- Include meaningful axis labels with appropriate units
- Use colorblind-friendly color schemes with sufficient contrast
- Add legends when using multiple colors or data series
- Keep visualizations simple and focused - avoid chart junk
- Select appropriate chart types for the data being presented
- Add annotations for important data points or patterns
- Ensure text readability (appropriate font size and contrast)
- Use consistent formatting across multiple visualizations
- Display data values directly on the visualizations if the data is appropriate for it.
- Make sure the labels do not overlap each other
- Create tooltips in human-readable format with appropriate units  (Eg : '₹54.00 Billion', 30 %, 29 Tonnes)

WORKFLOW - FOLLOW THESE STEPS IN ORDER:

STEP 1: PLANNING PHASE
- Analyze the user query to understand what visualizations are needed
- Decide if you have enough information to create the visualizations
- If not, explore the datasets to get more information
- Determine the best visualization types if user hasn't specified any
- Plan all visualizations that need to be created

STEP 2: GENERATION PHASE
- Generate ALL necessary visualizations in this phase
- Create each visualization by calling the run_python_code tool
- Save each visualization to both JSON and PNG formats
- If multiple visualizations are needed, create them one at a time but DO NOT call get_feedback between them
- Continue creating all visualizations until all necessary charts are completed
- If retrying, mention in status message that you are updating the visualisation

STEP 3: FEEDBACK PHASE (ONLY AFTER ALL VISUALIZATIONS ARE CREATED)
- Once ALL visualizations are generated, call get_feedback_for_images tool ONCE with all PNG paths
- This single call will analyze all visualizations together and provide comprehensive feedback
- DO NOT call get_feedback_for_images after each individual visualization
- DO NOT proceed to this step until all visualizations are created

STEP 4: IMPROVEMENT PHASE
- Review the feedback received for all visualizations
- If the feedback indicates improvements are needed (rating < 7 or specific issues mentioned):
  * Regenerate ONLY the visualizations that need improvement
  * The feedback will specify which visualizations need to be fixed
- If the feedback is positive, proceed to the next step

STEP 5: FINALIZATION PHASE
- Use the ResultPaths tool to return the paths to the JSON files that contain the visualizations
- Include a short 'status_message' (<=120 chars) that describes finalizing/saving results

CRITICAL RULES:
- DO NOT use parallel tool calling - call tools one at a time sequentially
- DO NOT call get_feedback_for_images after each individual visualization
- ONLY call get_feedback_for_images ONCE after ALL visualizations are created
- Generate all necessary visualizations BEFORE requesting feedback
- Always use the ResultPaths tool to return JSON file paths
- Begin by clearly considering visualization types and details based on user query and datasets
- Prioritize accessibility and professional appearance in all visualizations
- Do not mention about saving to json or png in the status messages
"""

    human_template_str = "{input}"

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(input=input_content)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]


def format_visualization_input(
    user_query: str,
    datasets_csv_info: str,
    previous_python_code: str,
    feedback_count: int,
    tool_call_count: int,
) -> dict:
    human_content_str = f"""\
This is the user query: {user_query}

The following are the datasets and their descriptions for the present query:

{datasets_csv_info}

CURRENT TOOL USAGE STATUS:
- Python code executions (run_python_code): {tool_call_count} times
- Feedback requests (get_feedback_for_images): {feedback_count} times
"""

    previous_python_text = """\
PREVIOUS PYTHON CODE:
The following code was used to generate previous visualizations. Note that CSV file paths
may have changed, so use the new paths provided in your current implementation.

```python
{previous_python_code}
```
"""

    human_content = human_content_str.format(
        user_query=user_query,
        datasets_csv_info=datasets_csv_info,
        tool_call_count=tool_call_count,
        feedback_count=feedback_count,
    )

    if previous_python_code:
        human_content += previous_python_text.format(previous_python_code=previous_python_code)

    return {"input": human_content}
