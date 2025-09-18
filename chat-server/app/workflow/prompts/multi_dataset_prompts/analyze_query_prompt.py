from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.workflow.prompts.formatters.format_prompt_for_langsmith import (
    langsmith_compatible,
)


def create_analyze_query_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
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

## CLASSIFICATION TYPES - Select exactly ONE:

1. "conversational" - Handle directly with available tools or context
- Simple dataset exploration: "What datasets are available?", "Show me table schemas"
- Basic data validation: "Is there data for 2023?", "What columns exist in sales table?"
- System capabilities: "Hello", "What can you do?", "Help me understand the data"
- Queries answerable from provided context/previous conversation
- Single-step information gathering that tools can handle completely
- Extremely vague queries needing clarification

Examples to handle HERE ("conversational"):
✓ "List all available datasets"
✓ "What's the schema of the elections table?"
✓ "Show me sample data from sales dataset"
✓ "What years of data do we have?"
✓ "How many records are in the customer table?"

2. "data_query" - Hand off to full workflow for complex processing
- Complex analytical queries requiring multiple steps
- Queries needing data aggregation, filtering, or calculations
- Multi-dataset analysis or comparisons
- Trend analysis, statistical computations, or insights generation
- Queries requiring SQL generation and execution
- Any query needing actual data processing beyond simple metadata
- Default choice when unsure between classifications

Examples to HAND OFF ("data_query"):
✓ "Show sales trends over the last 3 years"
✓ "Compare voter turnout between different states"
✓ "What are the top performing products by revenue?"
✓ "Analyze customer demographics and purchasing patterns"
✓ "Find correlations between marketing spend and sales"

## DECISION FRAMEWORK:

Primary Rules:
1. Can available tools completely answer the query? → "conversational"
2. Needs SQL generation or data processing? → "data_query"
3. Simple metadata/schema lookup? → "conversational"
4. Complex analysis or calculations? → "data_query"
5. When uncertain → "data_query"

Tool Usage:
- You can call tools directly within conversational queries
- Follow each tool's specific usage documentation and boundaries
- If previous tool calls failed or gave incomplete answers → Use "data_query"
- If tool documentation explicitly prohibits usage → Use "data_query"

Special Cases:
- Truncated SQL results are acceptable (due to large result sizes)
- If more than two tool calls fails route to "data_query"
- Extremely vague queries get clarification in "conversational" mode

CONFIDENCE SCORING (1-10):
- 8-10 (High): Clear simple metadata queries or obvious complex analytical queries
- 4-7 (Medium): Ambiguous queries that could benefit from tool exploration
- 1-3 (Low): Uncertain queries needing more context or dataset verification

RESPONSE FORMAT:

If tool call required:
- Call the tool directly (no JSON response)
- Include a user-friendly message along with the tool call (<= 120 characters)

If no tool call required:
{
    "query_type": "data_query" OR "conversational",
    "confidence_score": <integer from 1 to 10>,
    "reasoning": "Brief explanation including complexity assessment",
    "clarification_needed": "If vague, specify what you need",
    "status_message": "User-friendly next steps (<= 120 characters)"
}

Reasoning Examples:
- "Simple metadata query - can be handled with available tools"
- "Complex analytical query requiring SQL - needs full workflow"
- "Basic dataset exploration that tools can handle completely"
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


def format_analyze_query_input(
    user_query: str,
    tool_results: str | list | None = None,
    tool_call_count: int = 0,
    dataset_ids: list | None = None,
    project_ids: list | None = None,
    **kwargs,
) -> dict:
    """
    Format inputs for the analyze query prompt.

    Formats the user query, tool results, and metadata into a structured format
    suitable for the analyze query prompt processing.

    Args:
        user_query (str): The user's question to be analyzed
        tool_results (str | list | None, optional): Results from previous tool calls
        tool_call_count (int, optional): Number of tool calls made so far. Defaults to 0.
        dataset_ids (list | None, optional): List of dataset identifiers. Defaults to None.
        project_ids (list | None, optional): List of project identifiers. Defaults to None.
        **kwargs: Additional keyword arguments

    Returns:
        dict: Dictionary with formatted input parameters for the analyze query prompt
    """
    if tool_results is None:
        formatted_tool_results = ""
    elif isinstance(tool_results, list):
        if not tool_results:
            formatted_tool_results = ""
        else:
            formatted_results = []
            for i, result in enumerate(tool_results, 1):
                if hasattr(result, "content"):
                    formatted_results.append(f"Tool {i}: {result.content}")
                else:
                    formatted_results.append(f"Tool {i}: {str(result)}")
            formatted_tool_results = "\n".join(formatted_results)
    else:
        formatted_tool_results = str(tool_results)

    if dataset_ids is None:
        dataset_ids = []
    if project_ids is None:
        project_ids = []

    return {
        "user_query": user_query,
        "tool_results": formatted_tool_results,
        "tool_call_count": tool_call_count,
        "dataset_ids": dataset_ids,
        "project_ids": project_ids,
    }
