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

    system_content = """

You are an expert data visualization engineer. Use altair to create visualizations, and save them to json.
Do not create the data, read the data from the csv_path where the data is stored.
Use the run_python_code tool to run python code.
The datasets are already saved in the python sandbox with the specified file names.

IMPORTANT VISUALIZATION DIRECTIVES (Think about all of these before creating the visualizations):
- Add clear, descriptive titles to all visualizations
- Include meaningful axis labels with appropriate units
- Use color schemes that are colorblind-friendly and have sufficient contrast
- Add legends when using multiple colors or data series
- Keep visualizations simple and focused - avoid chart junk
- Use appropriate chart types for the data
- Add annotations for important data points or patterns
- Ensure text is readable (appropriate font size and contrast)
- Use consistent formatting across multiple visualizations
- Display data values directly on the visualizations if the data is appropriate for it.
- Make sure the labels do not overlap each other

Follow the steps below to create the visualizations:

REMEMBER TO FOLLOW ALL THESE STEPS
1. Decide if you have enough information to create the visualizations, otherwise explore the datasets to get more information.
2. Find the best way to visualize the data if the user has not specified any visualization type.
3. Use altair to create visualizations, and save them to json and png.
4. Use the run_python_code tool to run python code.
5. Get feedback for the generated image using the get_feedback_for_image tool.
6. Incorporate the feedback and edit the visualizations.
7. Use the ResultPaths tool to return the paths to the json files that contain the visualizations.

Use the ResultPaths tool to return the paths to the json.
First start by thinking clearly about the type of visualizations, and all the details about the visualizations based on the user query and the datasets.
"""

    human_template_str = """This is the user query: {user_query}

The following are the datasets and their descriptions for the present query:

{datasets_csv_info}
"""
    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    previous_python_text = """
Previous python code - This is the python code that was used to generate the previous visualization,
Please note that the paths to csv files might have changed so use the new paths in the code you are going to run.

```python
{previous_python_code}
```
"""

    human_content = human_template_str.format(
        user_query=user_query,
        datasets_csv_info=datasets_csv_info,
    )

    if previous_python_code:
        human_content += previous_python_text.format(previous_python_code=previous_python_code)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
