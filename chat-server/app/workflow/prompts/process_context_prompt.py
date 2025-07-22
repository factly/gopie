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

    system_content = """You are a context analyzer. Your task is to analyze the conversation history and current query to provide enhanced context for better data analysis.

Given the chat history and current query, you should:
1. Extract relevant context from previous messages that might help understand the current question
2. Extract and preserve any relevant SQL queries from previous assistant responses that could be useful for the current query
3. Enhance the current query by adding necessary context or making it more specific based on the conversation
4. IMPORTANT: If the previous query involved SQL or dataset information, ALWAYS include details about the specific dataset(s) used in your context summary
5. CRITICAL FOR MULTIDATASET QUERIES: If the user is asking to modify a previous SQL query, reuse the EXACT SAME dataset(s) that were used in the previous query. Don't select different datasets for related follow-up questions.
6. Determine if the current query is a follow-up question to the previous query.
7. SINGLE DATASET LOGIC: If only one dataset ID is provided in the initial request, this is a single dataset query - set need_semantic_search=false and required_dataset_ids=[] (empty array) since semantic search and multiple datasets are only for multi-dataset scenarios.
8. VISUALIZATION DATA: If (and only if) the current query is BOTH a follow-up question, with no additional data or info requests AND explicitly requests to VISUALIZE ("plot", "chart", "graph", "visualize", etc.) the RESULT of the previous query, you must also return the data needed for that visualization in the new \"visualization_data\" field. Otherwise this field should be an empty list.
9. SQL EXECUTION FOR VISUALIZATION: For visualization follow-ups, ALWAYS include SQL queries ONLY from the LATEST assistant response in the chat history (the most recent query result that the user wants to visualize), even if visualization_data is available (to handle cases where previous results were truncated).

FIELD DEFINITIONS (populate **all** fields exactly as specified):
- is_follow_up (boolean):
  • true  - the current query logically refers to, builds on, or wants to modify the immediately preceding query/answer.
  • false - the current query is standalone or unrelated.

- need_semantic_search (boolean):
  • true  - additional datasets must be searched for to answer the query (e.g. new topic, unspecified dataset) AND this is NOT a single dataset request.
  • false - all necessary datasets are already known from context or provided IDs, OR this is a single dataset request (only one dataset_id provided).

- required_dataset_ids (string[]):
  • For single dataset requests (only one dataset_id provided): ALWAYS return empty array [] regardless of context.
  • For multi-dataset scenarios (dataset id will be empty as there will be project id where there would be multiple datasets): Include every dataset ID that the answer depends on (Only previous).
  • Keep previously-used IDs if still relevant.
  • NEVER invent IDs.

- enhanced_query (string):
  • Rewrite the user query so it is self-contained and unambiguous, injecting any critical context (dates, filters, dataset names, etc.) gleaned from the chat history.
  • Keep the user's intent and wording where possible.

- context_summary (string):
  • Briefly explain the relationship between the current query and prior messages.
  • MUST list dataset IDs used previously, any SQL queries run, and explanatory details (tables, columns, filters, etc.).
  • Keep it concise—one or two sentences is ideal.

- visualization_data (object[]): *Only for visualization follow-ups*
  • Each element must have keys: data (list[list[Any]]), description (string), csv_path (null or string).
  • The description should be a short description of the data and the column description for each column.
  • The data follows the following format:
    - Each list in the data list is a row
    - The first row is the header row (column names)
    - All the remaining rows are the data rows
  • Provide tabular data extracted from the prior assistant result that the user wants visualized.
  • If no visualization is requested or the user want's visualization but also wants to do some other thing that just don't rely on visualization from the available data from chat history, return an empty list [].

- previous_sql_queries (string[]): *For follow-up queries and visualizations*
  • Extract relevant SQL statements from previous assistant responses in the chat history that could be useful for the current query.
  • For visualization follow-ups: ONLY include SQL queries from the LATEST (most recent) assistant response in the chat history, as the user wants to visualize the last results.
  • For other follow-up queries: Include SQL if it provides relevant context or data for the current question.
  • Return empty array [] if no relevant SQL queries exist in chat history.

- prev_csv_paths (string[]): *For visualization follow-ups only*
  • If the current query is BOTH a visualization follow-up AND only requesting visualization changes (like changing chart type, removing columns, etc.) WITHOUT requesting new data, include CSV file paths from the LATEST (most recent) assistant response in chat history.
  • These paths should be from visualization results, result_paths tool calls, or any CSV file references in the last assistant response.
  • This field enables reusing previous query results for visualization modifications.
  • Return empty array [] if not a visualization follow-up or if new data is being requested.

IMPORTANT: When referencing SQL queries in context_summary, use the actual table names (e.g., 'sales_data'), NOT dataset-ID-prefixed names (e.g., 'a7f392e1c8d4b5.sales'). Dataset IDs are only for tracking in required_dataset_ids.

SINGLE DATASET DETECTION:
- If only one dataset_id is provided in the initial request, this indicates a single dataset scenario
- For single dataset scenarios: need_semantic_search=false, required_dataset_ids=[]
- This is because semantic search and dataset tracking are multi-dataset features

VISUALIZATION LOGIC:
- If current query is visualization follow-up AND previous response has sufficient data → use visualization_data, also include previous_sql_queries from latest response
- If current query is visualization follow-up → always populate previous_sql_queries with SQL from the LATEST assistant response only
- If current query is visualization follow-up requesting ONLY visualization changes (no new data) → populate prev_csv_paths with CSV file paths from the LATEST assistant response
- If not a visualization follow-up → set previous_sql_queries based on relevance to current query

Be concise but thorough. Focus on information that would help a data analyst understand what the user is really asking for.

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
        current_query=current_query,
        chat_summary=chat_summary,
        dataset_ids=dataset_ids or []
    )

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
