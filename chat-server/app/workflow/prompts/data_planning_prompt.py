from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def data_planning_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are a data planning assistant. Given a resolved user query and conversation context,
determine what data operations are needed to fulfill the request.

ANALYSIS CRITERIA:

1. NEW DATA REQUIREMENTS (`is_new_data_needed`):
   • Assess if previously executed SQL queries contain sufficient data to answer the current query
   • TRUE: Need to execute new SQL or modify existing query
   • FALSE: Previous SQL queries contain adequate data to answer the query
   • When is_follow_up is FALSE, this is almost always TRUE (new independent query needs new data)

2. VISUALIZATION REQUIREMENTS (`generate_visualization`):
   • Determine whether the query requires visualization based on:
     - Explicit requests: chart types (pie, bar, line, scatter, histogram, etc.)
     - Keywords: "visualize", "plot", "graph", "chart", "show me a chart"
   • Only set TRUE for explicit visualization requests
   • Do NOT assume visualization is needed just because data is tabular

3. RELEVANT SQL QUERIES (`previous_sql_queries`):
   • Select the most relevant SQL queries from previously executed queries in conversation history
   • For modifications, prioritize the most recent relevant query
   • ONLY select from previously used SQL queries - do not invent new ones
   • Do not modify existing queries - only select by ID
   • Output the IDs of selected SQL queries
   • If is_follow_up is FALSE or no relevant queries exist, return an empty list

4. SQL MODIFICATION TYPE (`sql_modification_type`):
   • Applicable when is_follow_up is TRUE AND user wants to modify/combine previous queries
   • Identifies what kind of change the user wants to the previous query
   • Examples: "combine_tables", "add_column", "add_filter", "change_aggregation", "change_sort", "change_grouping"
   • Set to an empty string ("") when:
     - is_follow_up is FALSE
     - is_new_data_needed is FALSE
     - The query is answerable from existing data

IMPORTANT GUIDELINES:
- If is_follow_up is FALSE, set sql_modification_type to "" and previous_sql_queries to []
- Focus purely on data operation decisions
- Do NOT modify or enhance the query - that has already been done
- Base your decisions on the resolved query and available schemas
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


def format_data_planning_input(
    enhanced_query: str,
    is_follow_up: bool,
    context_summary: str,
    formatted_chat_history: str,
    schemas: str,
) -> dict:
    follow_up_status = (
        "Yes - this query builds on previous conversation"
        if is_follow_up
        else "No - this is an independent query"
    )

    formatted_input = f"""\
RESOLVED USER QUERY: {enhanced_query}

IS FOLLOW-UP: {follow_up_status}

CONTEXT SUMMARY: {context_summary if context_summary else "(No previous context)"}

PREVIOUS CONVERSATION HISTORY (with SQL query IDs):
{formatted_chat_history if formatted_chat_history else "(No previous conversation)"}

DATASET SCHEMAS (Note: Only first 5 datasets are shown):
{schemas if schemas else "(No schemas available)"}

TASK: Based on the above, determine what data operations are needed. Return ONLY a JSON response with the specified fields.

Note: SQL queries in the conversation history have IDs (e.g., [id:1]). Use these IDs when selecting relevant queries.
"""

    return {"input": formatted_input}
