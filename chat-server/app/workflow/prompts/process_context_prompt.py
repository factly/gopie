from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def create_process_context_prompt(
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
   • FALSE: Query is independent and unrelated to conversation history

2. NEW DATA REQUIREMENTS (`is_new_data_needed`):
   • Assess if previously executed SQL queries contain sufficient data to answer the current query
   • TRUE: Previous SQL queries lack sufficient data for the current query
   • FALSE: Previous SQL queries contain adequate data to answer the query

3. VISUALIZATION REQUIREMENTS (`generate_visualization`):
   • Determine whether the query requires visualization based on:
     - Explicit requests: chart types (pie, bar, line, scatter, histogram, etc.)
     - Keywords: "visualize", "plot", "graph", "chart".
     - Consider special instructions when evaluating visualization needs

4. RELEVANT SQL QUERIES (`relevant_sql_queries`):
   • Select the most relevant SQL queries from previously executed queries
   • Be comprehensive in selecting relevant queries
   • ONLY select from previously used SQL queries - do not invent new ones
   • Do not modify existing queries - only select by ID
   • Output the IDs of selected SQL queries

5. ENHANCED QUERY (`enhanced_query`):
   • Rewrite the user query as a NATURAL LANGUAGE QUESTION (never SQL)
   • Make it self-contained and unambiguous by injecting critical context
   • Include: dates, filters, dataset names, and other relevant context from conversation history
   • Preserve user's intent and wording where possible
   • DO NOT suggest specific technical approaches, methods, or how data should be retrieved
   • DO NOT guide whether to use fuzzy matching, SQL operations, or specific dataset selection strategies
   • Focus purely on clarifying WHAT the user wants, not HOW it should be obtained
   • If chat history is empty: combine user query with special instructions
   • Maintain user perspective in the enhanced query

6. CONTEXT SUMMARY (`context_summary`):
   • Summarize how the current query relates to previous conversation history
   • If chat history is empty: leave context summary empty
   • Focus on relevant connections and dependencies

IMPORTANT GUIDELINES:
- Always incorporate special instructions into the enhanced query
- The enhanced_query field MUST be natural language, never SQL or code
- Maintain consistency with previous analysis patterns
- Ensure all analysis fields are properly populated
- Consider both explicit and implicit user requirements
- DO NOT provide workflow suggestions or technical implementation guidance
- Focus on understanding user intent, not prescribing technical solutions
- Let downstream nodes determine the appropriate technical approach
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
    formatted_chat_history: list[str],
    project_custom_prompts: dict,
    schemas: list[str],
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
{formatted_chat_history}

SPECIAL INSTRUCTIONS:
{formatted_custom_prompts}

DATASET SCHEMAS PROVIDED FOR CURRENT QUERY (Note: Only first 5 datasets are shown here in the context):
{schemas}

TASK: Analyze the above information and return ONLY a single JSON response with the specified fields.
"""

    return {"input": formatted_input}
