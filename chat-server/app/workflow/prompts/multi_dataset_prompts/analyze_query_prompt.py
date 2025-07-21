from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.workflow.prompts.formatters.format_prompt_for_langsmith import langsmith_compatible


def create_analyze_query_prompt(
    **kwargs,
) -> list | ChatPromptTemplate:
    """
    Generate a prompt for classifying a user query as either "data_query" or "conversational" based on detailed guidelines and context.

    Depending on the `prompt_template` flag, returns either a `ChatPromptTemplate` for dynamic prompt construction or a list of message objects ready for use in a chat-based classification system. The prompt incorporates the user query, previous tool results, tool call count, dataset IDs, and project IDs, and provides comprehensive instructions for accurate query classification.

    Parameters:
        prompt_template (bool, optional): If True, returns a `ChatPromptTemplate` object; otherwise, returns a list of message objects.
        user_query (str, optional): The user's input query to be classified.
        tool_results (str, optional): Results from previous tool calls, if any.
        tool_call_count (int, optional): Number of tool calls made so far.
        dataset_ids (list, optional): List of dataset identifiers relevant to the query.
        project_ids (list, optional): List of project identifiers relevant to the query.

    Returns:
        list | ChatPromptTemplate: A list of message objects or a `ChatPromptTemplate` for use in a chat or classification workflow.
    """
    prompt_template = kwargs.get("prompt_template", False)
    user_query = kwargs.get("user_query", "")
    tool_results = kwargs.get("tool_results", "")
    tool_call_count = kwargs.get("tool_call_count", 0)
    dataset_ids = kwargs.get("dataset_ids", [])
    project_ids = kwargs.get("project_ids", [])

    system_content = """
You are a data query classifier. Analyze the user query and take appropriate action.
Prevent hallucination - only answer based on available context.

QUERY TYPES - Select exactly ONE:

1. "data_query" - Requires database access or data analysis
   * Examples: "Show sales trends", "Where were elections held last year"
   * Use when asking for specific data that needs database retrieval
   * Default choice when unsure between classifications
   * Use if previous tool calls failed to provide adequate answers

2. "conversational" - Answerable with available context, tools, or extremely
   vague queries needing clarification
   * Use for:
     a) Greetings, help requests: "Hello", "What can you do?"
     b) Questions answerable from provided context/previous conversation
     c) Extremely vague queries where no reasonable assumptions possible
     d) Queries that can be answered by calling available tools
   * You can call tools directly from conversational mode if needed
   * If tools provide incomplete answers, change to "data_query"
   * NEVER use for specific facts/events without available context/tools

TOOL USAGE GUIDELINES:
* You can use tools within conversational queries
* Evaluate if previous tool calls successfully answered the query
* ALWAYS refer to each tool's documentation for specific usage conditions:
  - Check the "ONLY use this tool when:" section for appropriate scenarios
  - Check the "DO NOT use this tool when:" section for inappropriate scenarios
  - Follow the tool's specific guidelines about when it should and shouldn't be used
* If a tool's documentation indicates it's NOT appropriate for the current query:
  - Consider classifying as "data_query" to use the full workflow instead
* If a tool call failed or gave incomplete information:
  - Consider classifying as "data_query" to use database search
* If previous tool calls successfully answered the query:
  - Maintain conversational classification

HANDLING TRUNCATED RESULTS:
  - Truncated results from running SQL query results are due to large result sizes and are visile to the user for analysis, so don't consider them as unsuccessful queries

GENERAL TOOL DECISION PROCESS:
1. Read the user query carefully
2. Check available tools and their usage documentation
3. If a tool explicitly states it handles this type of query → Use the tool
4. If a tool explicitly states it should NOT be used for this query → Don't use it
5. If the tool documentation mentions there's already a full workflow for such queries → Use "data_query" instead
6. When in doubt about tool appropriateness → Default to "data_query"

CORE RULES:
- Tool documentation takes precedence over general assumptions
- Respect tool usage boundaries as defined in their descriptions
- When tools indicate there's already a workflow → Use "data_query"
- Unknown facts/events without appropriate tools → "data_query"
- When unsure → "data_query"
- Clarification only for extremely vague queries
- Let data retrieval handle specific filtering
- Failed tool calls → "data_query"

DECISION PRIORITY:
1. Tool documentation explicitly covers the query → Use the tool (conversational)
2. Tools can completely answer → "conversational"
3. Needs data/unsure → "data_query"
4. Available context → "conversational"
5. Extremely vague → "conversational" with clarification

CONFIDENCE SCORE:
- Provide a confidence score (1-10) for your classification
- 1-3: Low confidence, might need verification with dataset search
- 4-7: Medium confidence, could benefit from dataset verification
- 8-10: High confidence in classification decision

IF YOUR ANALYSIS DETERMINES THAT A TOOL CALL IS REQUIRED:
    Call the appropriate tool directly in your response and do not output any JSON.

IF NO TOOL CALL IS REQUIRED:
    FORMAT YOUR RESPONSE AS JSON:
    {
        "query_type": "data_query" OR "conversational",
        "confidence_score": <integer from 1 to 10>,
        "reasoning": "Brief explanation of classification decision",
        "clarification_needed": "If conversational due to vagueness, specify what you need"
    }
"""

    human_template_str = """
USER QUERY: {user_query}
PREVIOUS TOOL RESULTS: {tool_results}
NUMBER OF PREVIOUS TOOL CALLS: {tool_call_count}/5 (max 5 allowed)
DATASET IDS: {dataset_ids}
PROJECT IDS: {project_ids}
"""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=langsmith_compatible(system_content)),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(
        user_query=user_query,
        tool_results=tool_results,
        tool_call_count=tool_call_count,
        dataset_ids=dataset_ids,
        project_ids=project_ids,
    )

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
