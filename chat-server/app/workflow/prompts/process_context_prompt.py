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


def create_process_context_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    current_query = kwargs.get("current_query", "")
    chat_history = kwargs.get("chat_history", [])

    system_content = """You are a context analyzer. Your task is to analyze the conversation history and current query to provide enhanced context for better data analysis.

Given the chat history and current query, you should:
1. Extract relevant context from previous messages that might help understand the current question
2. Enhance the current query by adding necessary context or making it more specific based on the conversation
3. IMPORTANT: If the previous query involved SQL or dataset information, ALWAYS include details about the specific dataset(s) used in your context summary
4. CRITICAL FOR MULTIDATASET QUERIES: If the user is asking to modify a previous SQL query, reuse the EXACT SAME dataset(s) that were used in the previous query. Don't select different datasets for related follow-up questions.
5. Determine if the current query is a follow-up question to the previous query.
6. VISUALIZATION DATA: If (and only if) the current query is BOTH a follow-up question AND explicitly requests to VISUALIZE ("plot", "chart", "graph", "visualize", etc.) the RESULT of the previous query, you must also return the data needed for that visualization in the new \"visualization_data\" field. Otherwise this field should be an empty list.
7. SQL EXECUTION FOR VISUALIZATION: Only populate previous_sql_queries when the current query is a visualization follow-up but the previous response doesn't contain sufficient data for the requested visualization.

FIELD DEFINITIONS (populate **all** fields exactly as specified):
- is_follow_up (boolean):
  • true  - the current query logically refers to, builds on, or wants to modify the immediately preceding query/answer.
  • false - the current query is standalone or unrelated.

- need_semantic_search (boolean):
  • true  - additional datasets must be searched for to answer the query (e.g. new topic, unspecified dataset).
  • false - all necessary datasets are already known from context or provided IDs.

- required_dataset_ids (string[]):
  • Include every dataset ID that the answer depends on (both previous and new).
  • Keep previously-used IDs if still relevant.
  • Leave empty ([]) only if no dataset is yet known or there is need for semantic search.
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
  • Provide tabular data extracted from the prior assistant result that the user wants visualized.
  • If no visualization is requested or the user want's visualization but also wants to do some other thing that just don't rely on visualization from the available data from chat history, return an empty list [].

- previous_sql_queries (string[]): *SQL execution indicator for visualization*
  • ONLY populate this if ALL THREE conditions are met:
    1. The previous query contained SQL statements
    2. The current query is a visualization follow-up request
    3. The previous response data is insufficient for the requested visualization
  • Extract the actual SQL statements from previous assistant responses in the chat history.
  • Return empty array [] in all other cases.
  • NOTE: Non-empty array indicates SQL execution is needed, empty array means use existing data or no execution needed.

IMPORTANT: When referencing SQL queries in context_summary, use the actual table names (e.g., 'sales_data'), NOT dataset-ID-prefixed names (e.g., 'a7f392e1c8d4b5.sales'). Dataset IDs are only for tracking in required_dataset_ids.

DECISION LOGIC FOR VISUALIZATION:
- If current query is visualization follow-up AND previous response has sufficient data → use visualization_data, set previous_sql_queries=[]
- If current query is visualization follow-up AND previous response lacks data AND previous query had SQL → populate previous_sql_queries with the SQL statements
- If not a visualization follow-up → set previous_sql_queries=[]

Be concise but thorough. Focus on information that would help a data analyst understand what the user is really asking for.

RESPOND ONLY IN THIS JSON FORMAT:
{{
  "is_follow_up": boolean,
  "need_semantic_search": boolean,
  "required_dataset_ids": string[],
  "enhanced_query": string,
  "context_summary": string,
  "visualization_data": object[],
  "previous_sql_queries": string[]
}}
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

    human_template_str = """Current user query: {current_query}

Chat history: {chat_summary}

Analyze the above and return ONLY a single JSON response with the specified fields."""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(
        current_query=current_query, chat_summary=chat_summary
    )

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
