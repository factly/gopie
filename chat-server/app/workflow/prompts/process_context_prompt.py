from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.workflow.prompts.formatters.format_prompt_for_langsmith import (
    langsmith_compatible,
)


def create_process_context_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    current_query = kwargs.get("current_query", "")
    formatted_chat_history = kwargs.get("formatted_chat_history", [])

    system_content = """
You are a context analyzer. Your primary responsibility is to analyze the conversation history and
current query to determine the appropriate context and data requirements for processing the user's request.

Your analysis should follow these key criteria:

1. Is this a follow-up query? (`is_follow_up`)
  • If the user's query is a follow-up query from the conversation history, then the answer should be true.
  • If the user's query is independent and not related to the conversation history, then the answer should be false.

2. Does the user query require new data? (`is_new_data_needed`)
  • Determine if the previously used sql queries would have all the sufficient data to answer the user query.
  • If the previously used sql queries would not have all the sufficient data to answer the user query, then the answer should be true.

3. is the query related to visualization? (`is_visualization_query`)
  • Determine if the query is related to visualization.

4. relevant sql queries (`relevant_sql_queries`)
  • Select the most relevant sql queries from the previously selected sql queries based on the user query.
  • Be greedy in selecting the relevant sql queries.
  • Do not invent any sql queries. Only select from the previously used sql queries.
  • Do not modify the sql queries, only select from the previously used sql queries.

5. What is the enhanced query? (`enhanced_query`)
  • Rewrite the user query so it is self-contained and unambiguous, injecting any critical context (dates, filters, dataset names, etc.) gleaned from the chat history.
  • Keep the user's intent and wording where possible.
  • Make it clear whether user needs more data, new datasets, or just visualization.
  • If the chat history is empty, then the enhanced query should be the same as the user query.

6. Summary of the context (`context_summary`)
  • Provide a summary of how the present query is related to the previous conversation history.
  • If the chat history is empty, then the context summary should be empty.

RESPOND ONLY IN THIS JSON FORMAT:
{
  "is_follow_up": boolean,
  "is_new_data_needed": boolean,
  "is_visualization_query": boolean,
  "relevant_sql_queries": string[],
  "enhanced_query": string,
  "context_summary": string,
}
"""
    human_template_str = """
Current user query: {current_query}

Previous conversation history:
{formatted_chat_history}

Analyze the above and return ONLY a single JSON response with the specified fields."""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=langsmith_compatible(system_content)),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(
        current_query=current_query,
        formatted_chat_history=formatted_chat_history,
    )

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
