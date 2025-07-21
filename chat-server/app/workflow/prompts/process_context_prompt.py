from langchain_core.messages import (
    AIMessage,
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
    chat_history = kwargs.get("chat_history", [])
    dataset_ids = kwargs.get("dataset_ids", [])

    system_content = """You are a process context analyzer for the LLM. Your primary responsibility is to analyze the conversation history and current query to determine the appropriate context and data requirements for processing the user's request.

Your analysis should follow these 7 key criteria in order:

1. DATA SUFFICIENCY ANALYSIS:
   - Does the user need more columns/rows from already selected datasets?
   - Does the user need entirely new datasets not yet selected?
   - Does the current context have sufficient data based on previous SQL queries and visualizations?

2. VISUALIZATION CONTEXT CHECK:
   - Is the current query related to visualization of existing data?
   - If yes, identify and extract the latest visualization files/data from chat history

3. FOLLOW-UP DETECTION:
   - Determine if this is a follow-up question to previous queries
   - If follow-up, maintain consistency with previous context (datasets, filters, etc.)

4. RELEVANT DATASETS IDENTIFICATION:
   - From already selected datasets, which ones are relevant to the current query?
   - Include dataset descriptions and metadata for context
   - For follow-ups, reuse EXACT SAME datasets from previous queries when relevant

5. RELEVANT SQL QUERIES EXTRACTION:
   - Extract SQL queries from chat history that are relevant to current query
   - For visualizations: include SQL from LATEST assistant response only
   - For other follow-ups: include contextually relevant SQL queries

6. ENHANCED QUERY GENERATION:
   - Create a self-contained, enhanced version of the user query
   - Inject necessary context from conversation history
   - Preserve user's original intent while adding clarity

7. CONTEXT SUMMARY BUILDING:
   - Build comprehensive context summary based on points 1-6
   - Include relationship between current and previous queries
   - Mention dataset IDs, SQL queries used, and key contextual details

FIELD DEFINITIONS (populate **all** fields based on the 7 criteria analysis):

- is_follow_up (boolean): [Criteria 3 - Follow-up Detection]
  • true  - the current query logically refers to, builds on, or wants to modify the immediately preceding query/answer.
  • false - the current query is standalone or unrelated.

- need_semantic_search (boolean): [Criteria 1 - Data Sufficiency Analysis]
  • true  - additional datasets must be searched for to answer the query (user needs new datasets not yet selected).
  • false - all necessary datasets are already known from context or provided IDs, OR user only needs more columns/rows from existing datasets.

- required_dataset_ids (string[]): [Criteria 4 - Relevant Datasets Identification]
  • Include every dataset ID that the answer depends on from already selected datasets.
  • Keep previously-used IDs if still relevant for current query.
  • Include dataset descriptions and metadata context.
  • NEVER invent IDs.

- enhanced_query (string): [Criteria 6 - Enhanced Query Generation]
  • Rewrite the user query so it is self-contained and unambiguous, injecting any critical context (dates, filters, dataset names, etc.) gleaned from the chat history.
  • Keep the user's intent and wording where possible.
  • Make it clear whether user needs more data, new datasets, or just visualization.

- context_summary (string): [Criteria 7 - Context Summary Building]
  • Build from criteria 1-6: explain data sufficiency, visualization context, follow-up relationship, relevant datasets used, and SQL queries executed.
  • MUST list dataset IDs used previously, any SQL queries run, and explanatory details (tables, columns, filters, etc.).
  • Keep it concise—one or two sentences per major context element.

- visualization_data (object[]): [Criteria 2 - Visualization Context Check]
  • Each element must have keys: data (list[list[Any]]), description (string), csv_path (null or string).
  • The description should be a short description of the data and the column description for each column.
  • The data follows the following format:
    - Each list in the data list is a row
    - The first row is the header row (column names)
    - All the remaining rows are the data rows
  • Provide tabular data extracted from the prior assistant result that the user wants visualized.
  • If current query is NOT related to visualization, return an empty list [].
  • If user wants visualization but also requests additional data/analysis, return an empty list [].

- previous_sql_queries (string[]): [Criteria 5 - Relevant SQL Queries Extraction]
  • Extract relevant SQL statements from previous assistant responses in the chat history that could be useful for the current query.
  • For visualization follow-ups: ONLY include SQL queries from the LATEST (most recent) assistant response in the chat history, as the user wants to visualize the last results.
  • For other follow-up queries: Include SQL if it provides relevant context or data for the current question.
  • Consider data sufficiency: if user needs more data, include SQL that shows what was previously queried.
  • Return empty array [] if no relevant SQL queries exist in chat history.

- prev_csv_paths (string[]): *For visualization follow-ups only*
  • If the current query is BOTH a visualization follow-up AND only requesting visualization changes (like changing chart type, removing columns, etc.) WITHOUT requesting new data, include CSV file paths from the LATEST (most recent) assistant response in chat history.
  • These paths should be from visualization results, result_paths tool calls, or any CSV file references in the last assistant response.
  • This field enables reusing previous query results for visualization modifications.
  • Return empty array [] if not a visualization follow-up or if new data is being requested.

IMPORTANT: When referencing SQL queries in context_summary, use the actual table names (e.g., 'sales_data'), NOT dataset-ID-prefixed names (e.g., 'a7f392e1c8d4b5.sales'). Dataset IDs are only for tracking in required_dataset_ids.

VISUALIZATION LOGIC:
- If current query is visualization follow-up AND previous response has sufficient data → use visualization_data, also include previous_sql_queries from latest response
- If current query is visualization follow-up → always populate previous_sql_queries with SQL from the LATEST assistant response only
- If current query is visualization follow-up requesting ONLY visualization changes (no new data) → populate prev_csv_paths with CSV file paths from the LATEST assistant response
- If not a visualization follow-up → set previous_sql_queries based on relevance to current query

ANALYSIS PROCESS:
1. First, analyze data sufficiency: Does user need more columns/rows from existing datasets, new datasets entirely, or is current data sufficient?
2. Then check visualization context: Is this a visualization request for existing data?
3. Determine follow-up status: Does this build on previous queries?
4. Identify relevant datasets from already selected ones with their descriptions
5. Extract relevant SQL queries from chat history
6. Generate enhanced query that's self-contained with injected context
7. Build comprehensive context summary based on above analysis

Be concise but thorough. Focus on information that would help a data analyst understand what the user is really asking for based on the 7-criteria analysis.

RESPOND ONLY IN THIS JSON FORMAT:
{
  "is_follow_up": boolean,
  "need_semantic_search": boolean,
  "required_dataset_ids": string[],
  "enhanced_query": string,
  "context_summary": string,
  "visualization_data": object[],
  "previous_sql_queries": string[],
  "prev_csv_paths": string[]
}
"""

    if chat_history and len(chat_history) > 0:
        formatted_history = []

        for msg in chat_history:
            if isinstance(msg, AIMessage):
                content = f"Assistant: {str(msg.content)}\n"
            elif isinstance(msg, HumanMessage):
                content = f"User: {str(msg.content)}\n"
            else:
                content = str(msg) + "\n"

            formatted_history.append(content + "\n\n")

        chat_summary = formatted_history
    else:
        chat_summary = ["No previous conversation"]

    human_template_str = """
Current user query: {current_query}

Chat history: {chat_summary}

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
        current_query=current_query, chat_summary=chat_summary, dataset_ids=dataset_ids or []
    )

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
