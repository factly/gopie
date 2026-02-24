from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def generate_subqueries_prompt(**kwargs) -> list | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    user_input = kwargs.get("user_input", "")
    context_info = kwargs.get("context_info", "")

    system_content = """
Analyze the user query and determine if it needs to be broken down into sub-queries.

SQL MODIFICATION REQUESTS (CRITICAL - PLEASE NOTICE THIS):
  • Queries starting with [SQL_MODIFICATION: <type>] are follow-up requests to modify previous SQL results
  • By their nature, these queries don't require breakdown since they reference existing data
  • Examples you might see: "[SQL_MODIFICATION: add_column]...", "[SQL_MODIFICATION: combine_tables]..."
  • When you see this pattern, recognize it indicates the user wants to work with previous results, not fetch new data

QUERY ASSESSMENT:
  - Determine if the query can be handled in a single agent cycle
  - Consider complexity, number of distinct data operations, and interdependent steps
  - Be EXTREMELY conservative about breaking down queries
  - Default position should be NOT to break down queries unless absolutely necessary

DECISION CRITERIA:
  - Break down if the query requires multiple unrelated tasks or operations
  - Break down if the query has dependent steps where a later part relies on the outcome of an earlier part
  - Simple queries about a single topic that can be answered with a single operation should NOT be broken down
  - If unsure, DO NOT break down the query

COMPLEXITY INDICATORS (requiring breakdown):
  - Multiple unrelated questions in a single query
  - Multi-step analysis where subsequent steps depend on prior results
  - Questions requiring data from completely different domains
  - Analysis that requires results from previous operations

IF BREAKDOWN IS NEEDED, generate effective subqueries following these guidelines:

CONTEXT AWARENESS:
  - You have been provided with project context and available datasets
  - Use this information to understand what data is available and how it might be organized
  - If you see metadata or mapping datasets (e.g., datasets that map IDs to names, or link entities together), consider using them strategically
  - When a query requires data from multiple related datasets, consider if a metadata dataset can help identify which datasets to query

BREAKDOWN RULES:
  - Generate exactly 2 sub-queries based on actual complexity
  - Each sub-query must be in natural language only - NEVER generate SQL
  - Each sub-query should address a distinct aspect of the main question
  - Each sub-query should be self-contained and not assume knowledge of system architecture or data organization
  - Make each sub-query clear, specific, and focused on a single task
  - Ensure subqueries directly relate to the user's original intent
  - Focus on WHAT information is needed, not HOW to retrieve it

SMART DECOMPOSITION:
  - If the query asks for aggregated data across multiple entities (e.g., "all states", "all regions", "all categories"):
    * Check if there's a metadata/mapping dataset that can help identify relevant datasets
    * If so, consider creating subqueries that leverage this metadata for better coverage
  - If you notice dataset names follow patterns (e.g., state_CA, state_TX) or descriptions suggest partitioned data:
    * Frame subqueries to help the system identify all relevant partitions
  - The goal is to ensure complete data coverage, not just partial results from a limited sample

STRICT PROHIBITIONS:
  - NEVER generate SQL code or database queries
  - NEVER include implementation details about HOW to get information
  - NEVER hallucinate additional context or requirements
  - NEVER break down the query into process steps (like "first search for X, then analyze Y")
  - NEVER generate step-by-step information retrieval subqueries without knowing the actual system structure or data organization
  - NEVER create subqueries like "first get information about X" followed by "then get information about Y" unless you have explicit context about how this information is stored or organized
  - NEVER assume sequential data retrieval patterns without understanding the underlying data architecture
  - NEVER generate subqueries that imply a specific order of data collection without context about how the system is organized
  - Focus on generating conceptually distinct questions, not procedural steps for information gathering

IMPORTANT:
  - If breakdown is NOT needed, set needs_breakdown=false and leave subqueries empty
  - If breakdown IS needed, set needs_breakdown=true and provide exactly 2 subqueries
  - Ensure each subquery is a natural language question that a human would ask
"""

    human_template_str = """
{context_info}

User Query: {user_input}
"""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(user_input=user_input, context_info=context_info)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
