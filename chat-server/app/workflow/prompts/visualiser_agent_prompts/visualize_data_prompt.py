from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def create_visualize_data_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    user_query = kwargs.get("user_query", "")
    datasets_csv_info = kwargs.get("datasets_csv_info", "")
    previous_python_code = kwargs.get("previous_python_code", "")
    feedback_count = kwargs.get("feedback_count", 0)
    tool_call_count = kwargs.get("tool_call_count", 0)

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

Follow the steps below to create the visualizations:

REMEMBER TO FOLLOW ALL THESE STEPS
1. Decide if you have enough information to create the visualizations, otherwise explore the datasets to get more information.
2. Find the best way to visualize the data if the user has not specified any visualization type.
3. Use altair to create visualizations, and save them to json and png. Use the run_python_code tool to run python code. Always include a short 'status_message' that describes the next step in 1 sentence (<=120 chars). If retrying, mention it's a retry.
4. Get feedback for the generated image using the get_feedback_for_image tool. Always include a short 'status_message' (<=120 chars) describing the action, and mention if it's a retry.
5. Incorporate the feedback and edit the visualizations.
6. Use the ResultPaths tool to return the paths to the json files that contain the visualizations. Include a short 'status_message' (<=120 chars) that describes finalizing/saving results.

IMPORTANT NOTES:
- Always use the ResultPaths tool to return JSON file paths
- Begin by clearly considering visualization types and details based on user query and datasets
- Prioritize accessibility and professional appearance in all visualizations
"""

    human_template_str = """This is the user query: {user_query}

The following are the datasets and their descriptions for the present query:

{datasets_csv_info}

CURRENT TOOL USAGE STATUS:
- Python code executions (run_python_code): {tool_call_count} times
- Feedback requests (get_feedback_for_image): {feedback_count} times
"""
    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    previous_python_text = """
PREVIOUS PYTHON CODE:
The following code was used to generate previous visualizations. Note that CSV file paths
may have changed, so use the new paths provided in your current implementation.

```python
{previous_python_code}
```
"""

    human_content = human_template_str.format(
        user_query=user_query,
        datasets_csv_info=datasets_csv_info,
        tool_call_count=tool_call_count,
        feedback_count=feedback_count,
    )

    if previous_python_code:
        human_content += previous_python_text.format(previous_python_code=previous_python_code)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
