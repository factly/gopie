from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.workflow.prompts.formatters.format_prompt_for_langsmith import langsmith_compatible


def create_process_context_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    current_query = kwargs.get("current_query", "")
    dataset_ids = kwargs.get("dataset_ids", [])

    system_content = """
You are a context analyzer. Your primary responsibility is to analyze the conversation history and
current query to determine the appropriate context and data requirements for processing the user's request.

Your analysis should follow these 9 key criteria in order:

1. Is this a follow-up query? (`is_follow_up`)
  • If the user's query is a follow-up query from the conversation history, then the answer should be true otherwise false.

2. Is new data needed? (`new_data_needed`)
  • Determine if the user needs new data other than the data already processed in the previous queries.
  • For eg: user wants to add some other data needed or a asks for a completely new data or something else like that.

3. Does the user want a visualization? (`needs_visualization`)
  • If the user wants a visualization, then the answer should be true otherwise false.

4. What is the visualization data? (`visualization_data`)
  • If the user provided the data for the visualization, then format the data properly and add it to the visualization_data.
  • Each element must have keys: data (list[list[Any]]), description (string), csv_path (null or string).
  • The description should be a short description of the data and the column description for each column.
  • The data follows the following format:
    - Each list in the data list is a row
    - The first row is the header row (column names)
    - All the remaining rows are the data rows

5. What are the previous json paths? (`previous_json_paths`)
  • If the user wants to do some modification in the previously generated visualization, then add the previous json paths to the previous_json_paths.
  • Otherwise, set the previous_json_paths to an empty list.

6. What are the relevant datasets ids? (`relevant_datasets_ids`)
  • Always set the dataset ids of the last user/assistant message.
  • After setting the dataset ids with the last user/assistant message, then you can add other dataset ids if
    needed based on relevance to the user query, but the last used dataset ids should be always present.

7. What are the relevant sql queries? (`relevant_sql_queries`)
  • Always set the sql queries of the last user/assistant message.
  • After setting the sql queries of the last user/assistant message, then you can add other sql queries if
    needed based on relevance to the user query, but the last used sql query should be always present.

8. What is the enhanced query? (`enhanced_query`)
  • Rewrite the user query so it is self-contained and unambiguous, injecting any critical context (dates, filters, dataset names, etc.) gleaned from the chat history.
  • Keep the user's intent and wording where possible.
  • Make it clear whether user needs more data, new datasets, or just visualization.

9. What is the context summary? (`context_summary`)
  • Build the context for that covers all the criteria from 1-8.
  • The context should be in brief and expalin the decision making process for each criteria.

RESPOND ONLY IN THIS JSON FORMAT:
{
  "is_follow_up": boolean,
  "new_data_needed": boolean,
  "needs_visualization": boolean,
  "visualization_data": object[],
  "previous_json_paths": string[],
  "relevant_datasets_ids": string[],
  "relevant_sql_queries": string[],
  "enhanced_query": string,
  "context_summary": string,
}
"""
    human_template_str = """
Current user query: {current_query}

Dataset IDs provided: {dataset_ids}

Analyze the above and return ONLY a single JSON response with the specified fields."""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=langsmith_compatible(system_content)),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(
        current_query=current_query, dataset_ids=dataset_ids or []
    )

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
