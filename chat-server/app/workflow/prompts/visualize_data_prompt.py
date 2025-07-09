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
    datasets = kwargs.get("datasets", [])
    csv_paths = kwargs.get("csv_paths", [])

    system_content = """\
You are an expert data visualization engineer. Use altair to create visualizations, and save them to json.
Do not create the date, read the data from the csv_path where the data is stored.
Use the run_python_code tool to run python code.

Your task is the following:
1. Find the best way to visualize the data if the user has not specified any visualization type.
2. Use altair to create visualizations, and save them to json.
3. Use the run_python_code tool to run python code.
4. Return the paths to the json files that contain the visualizations.

First start by reasoning about the best way to visualize the data.
"""

    human_template_str = """This is the user query: {user_query}

The following are the datasets and their descriptions:

{datasets_csv_info}
"""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    datasets_csv_info = ""
    for idx, (dataset, csv_path) in enumerate(zip(datasets, csv_paths)):
        datasets_csv_info += f"Dataset {idx + 1}: \n\n"
        datasets_csv_info += f"Description: {dataset.description}\n\n"
        datasets_csv_info += f"CSV Path: {csv_path}\n\n"

    human_content = human_template_str.format(
        user_query=user_query, datasets_csv_info=datasets_csv_info
    )

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
