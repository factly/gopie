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
You are a context analyzer responsible for analyzing conversation history and current queries
to determine appropriate context and data requirements for processing user requests.

ANALYSIS CRITERIA:

1. FOLLOW-UP DETECTION (`is_follow_up`):
   • Determine if the user's query is a follow-up from conversation history
   • TRUE: Query builds upon or references previous conversation context
   • FALSE: Query is independent or user switches to a different topic

2. NEW DATA REQUIREMENTS (`is_new_data_needed`):
   • Assess if previously executed SQL queries contain sufficient data to answer the current query
   • TRUE: Need to execute new SQL or modify existing query
   • FALSE: Previous SQL queries contain adequate data to answer the query

3. VISUALIZATION REQUIREMENTS (`generate_visualization`):
   • Determine whether the query requires visualization based on:
     - Explicit requests: chart types (pie, bar, line, scatter, histogram, etc.)
     - Keywords: "visualize", "plot", "graph", "chart"
     - Consider special instructions when evaluating visualization needs

4. RELEVANT SQL QUERIES (`relevant_sql_queries`):
   • Select the most relevant SQL queries from previously executed queries
   • For modifications, prioritize the most recent relevant query
   • ONLY select from previously used SQL queries - do not invent new ones
   • Do not modify existing queries - only select by ID
   • Output the IDs of selected SQL queries

5. SQL MODIFICATION TYPE (`sql_modification_type`):
   • Only applicable when is_follow_up=TRUE and is_new_data_needed=TRUE
   • Identifies what kind of change the user wants to the previous query
   • Set to an empty string ("") for fresh queries or when answerable from existing data

6. ENHANCED QUERY (`enhanced_query`):
   • Keep the user's original query with minimal changes
   • Only resolve ambiguous pronouns (it, that, those, this data) with what they refer to
   • DO NOT add dataset names, project IDs, or technical terms
   • DO NOT suggest specific technical approaches or how data should be retrieved
   • Preserve user's intent and exact wording where possible

7. CONTEXT SUMMARY (`context_summary`):
   • Briefly describe what previous query/result the user is referring to
   • If chat history is empty or not a follow-up: leave empty
   • Focus on relevant connections and dependencies

8. STATUS MESSAGE (`status_message`):
   • Short user-friendly message acknowledging the request (1-2 sentences)

IMPORTANT GUIDELINES:
- Preserve the user's exact words and intent
- The enhanced_query field MUST be natural language, never SQL or code
- DO NOT provide workflow suggestions or technical implementation guidance
- Focus on understanding user intent, not prescribing technical solutions
- Let downstream nodes determine the appropriate technical approach
- If unsure whether it's a follow-up, prefer treating as a new query
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
    schemas: str,
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

DATASET SCHEMAS PROVIDED FOR CURRENT QUERY (Note: Only first 5 datasets are shown here in the context):
{schemas}

TASK: Analyze the above information and return ONLY a single JSON response with the specified fields.

Note: SQL queries in the conversation history have IDs (e.g., [id:1]). Use these IDs when selecting relevant queries.
"""

    return {"input": formatted_input}
