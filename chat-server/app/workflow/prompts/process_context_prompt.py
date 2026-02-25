from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def process_context_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are a query understanding assistant. Your ONLY job is to understand what the user
is asking by analyzing their current query in the context of conversation history.

ANALYSIS CRITERIA:

1. FOLLOW-UP DETECTION (`is_follow_up`):
   • Determine if the user's query is a follow-up from conversation history
   • TRUE: Query builds upon or references previous conversation context
   • FALSE: Query is independent or user switches to a different topic
   • If unsure, prefer treating as a new query (FALSE)

2. ENHANCED QUERY (`enhanced_query`):
   • Keep the user's original query with minimal changes
   • Only resolve ambiguous pronouns (it, that, those, this data) with what they refer to
   • DO NOT add dataset names, project IDs, or technical terms
   • DO NOT suggest specific technical approaches or how data should be retrieved
   • Preserve user's intent and exact wording where possible

3. CONTEXT SUMMARY (`context_summary`):
   • Briefly describe what previous query/result the user is referring to
   • If chat history is empty or not a follow-up: leave empty
   • Focus on relevant connections and dependencies

4. STATUS MESSAGE (`status_message`):
   • Short user-friendly message acknowledging the request (1-2 sentences)

IMPORTANT GUIDELINES:
- Preserve the user's exact words and intent
- The enhanced_query field MUST be natural language, never SQL or code
- DO NOT provide workflow suggestions or technical implementation guidance
- Focus on understanding user intent, not prescribing technical solutions
- Do NOT decide what data operations are needed - that is handled separately
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


def format_process_context_input(
    current_query: str,
    formatted_chat_history: str,
    project_custom_prompts: dict,
) -> dict:
    formatted_custom_prompts = (
        "\n\n".join(
            [
                f"Project ID: {project_id}\n{prompt}"
                for project_id, prompt in project_custom_prompts.items()
            ]
        )
        if project_custom_prompts
        else ""
    )

    formatted_input = f"""\
CURRENT USER QUERY: {current_query}

PREVIOUS CONVERSATION HISTORY:
{formatted_chat_history if formatted_chat_history else "(No previous conversation)"}

SPECIAL INSTRUCTIONS:
{formatted_custom_prompts if formatted_custom_prompts else "(None)"}

TASK: Analyze the above information and return ONLY a single JSON response with the specified fields.
"""

    return {"input": formatted_input}
