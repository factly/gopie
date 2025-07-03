from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
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

For the "required_dataset_ids" field:
- Include ALL dataset IDs that the current query depends on
- Include previous dataset IDs that are still relevant to the current query
- For new topics that might need semantic search, leave this empty or include only the previous datasets that are still relevant
- DO NOT make up dataset IDs - only include those explicitly mentioned in the conversation or clearly needed

For the "context_summary" field:
- ALWAYS include any dataset IDs mentioned in previous queries and responses
- Include ALL relevant SQL queries that were used previously (It should be represented as same as the SQL query in the chat history)
- Mention which dataset each SQL query was run against
- If specific tables, columns, or filters were used in previous queries, include those details
- Make sure to show the relationship between previous queries and the current query

IMPORTANT: When referencing SQL queries in context_summary, use the actual table names (like 'sales_data', 'covid_statistics') NOT dataset IDs (lik`e 'a7f392e1c8d4b5.sales'). Dataset IDs are for tracking which dataset was used, but SQL queries should use proper table names.

Be concise but thorough. Focus on information that would help a data analyst understand what the user is really asking for.

Examples of different scenarios:

1) Follow-up question using the same dataset:
   Chat history: ["Show me sales data for 2023", "The total was $1.2M across all regions. SQL used: SELECT SUM(amount) FROM sales_data WHERE year=2023"]
   Current query: "What about the trends?"

   Fields:
   - is_follow_up: true
   - need_semantic_search: false
   - required_dataset_ids: ["a7f392e1c8d4b5"]
   - enhanced_query: "What are the sales trends for 2023 data that showed $1.2M total across all regions?"
   - context_summary: "User previously queried dataset a7f392e1c8d4b5 with SQL 'SELECT SUM(amount) FROM sales_data WHERE year=2023' showing total $1.2M across regions. User now wants trend analysis on the same dataset."

2) Follow-up question needing previous dataset plus additional datasets:
   Chat history: ["Show me covid cases by state using e28c7b6d9a3f5", "Here's the SQL query: SELECT state, SUM(cases) FROM covid_statistics GROUP BY state"]
   Current query: "Now compare with vaccination rates by state"

   Fields:
   - is_follow_up: true
   - need_semantic_search: true
   - required_dataset_ids: ["e28c7b6d9a3f5", "7d9f3e8b1a6c2"]
   - enhanced_query: "Compare covid cases by state from e28c7b6d9a3f5 with vaccination rates by state"
   - context_summary: "Previous query used SQL 'SELECT state, SUM(cases) FROM covid_statistics GROUP BY state' on dataset e28c7b6d9a3f5 for state-level covid cases. Now need to compare with vaccination data (likely dataset 7d9f3e8b1a6c2) by state."

3) New question with no relevant previous context:
   Chat history: ["What's the weather like?", "It's sunny today."]
   Current query: "Show me sales data for Q1"

   Fields:
   - is_follow_up: false
   - need_semantic_search: true
   - required_dataset_ids: []
   - enhanced_query: "Show me sales data for Q1"
   - context_summary: ""

RESPOND ONLY IN THIS JSON FORMAT:
{{
  "is_follow_up": boolean,  // whether this is a follow-up question to the previous query
  "need_semantic_search": boolean,  // true if new datasets should be searched for
  "required_dataset_ids": string[],  // all dataset IDs needed for current query (both previous and new)
  "enhanced_query": string,  // refined version of current query with better context
  "context_summary": string  // summary of relevant context from chat history
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
                SystemMessagePromptTemplate.from_template(system_content),
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
