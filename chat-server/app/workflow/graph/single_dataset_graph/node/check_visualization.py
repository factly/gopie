from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.single_dataset_graph.types import State


@configure_node(
    role="intermediate",
    progress_message="Checking visualization needs...",
)
async def check_visualization(state: State, config: RunnableConfig) -> dict:
    user_query = state.get("user_query", "")

    raw_sql_queries_data = []
    query_result = state.get("query_result") or {}
    sql_queries = query_result.get("sql_queries", [])

    for result in sql_queries:
        if result.get("result") and result.get("success", True):
            raw_sql_queries_data.extend(result["result"])

    if not raw_sql_queries_data:
        return {
            "raw_sql_queries_data": raw_sql_queries_data,
            "wants_visualization": False,
            "reasoning": "",
        }

    prompt = f"""
You are a strict routing supervisor for a data analysis system.
Your job is to determine if the user EXPLICITLY and CLEARLY
requested data visualization.

CRITICAL RULES - Only return true if the user:
1. Uses explicit visualization words: "plot", "chart", "graph", "visualize",
                                      "visualization", "visual"
2. Requests specific chart types: "bar chart", "pie chart", "line graph",
                                  "scatter plot", "histogram"
3. Asks to create visual representations: "create a chart", "make a graph",
                                          "show me a plot"
4. Uses visualization verbs: "plot this", "chart the data", "graph the results"

NEVER return true for:
- General analysis questions: "What are the trends?", "Show me patterns"
- Data requests without visualization: "Show me the data", "Display..."
- Comparison questions: "Compare X and Y", "Which is higher?"
- Summary requests: "What are the top 10?", "Give me a summary"
- Trend analysis: "Show trends", "Analyze patterns"
                  (unless explicitly asking to visualize)
- Questions with "show" that don't specify visual format: "Show me the revenue"

Be extremely conservative. When in doubt, return false.

Examples that should return TRUE:
- "Create a bar chart of sales by region"
- "Plot the revenue over time"
- "Show me a pie chart of the distribution"
- "Visualize the data"
- "Graph the monthly trends"
- "Make a scatter plot"

Examples that should return FALSE:
- "What are the sales trends?" (analysis, not visualization)
- "Show me the top products" (data display, not chart)
- "Compare revenue across regions" (comparison, not visualization)
- "Display the monthly data" (data display, not chart)
- "Analyze the distribution" (analysis, not visualization)
- "Show me patterns in the data" (analysis, not visualization)

User question: {user_query}

Respond with JSON:
{{
    "wants_visualization": true/false,
    "reasoning": "clear explanation of why you chose true/false"
}}
    """

    llm = get_llm_for_node("supervisor", config)
    response = await llm.ainvoke(
        {
            "input": prompt,
            "chat_history": get_chat_history(config),
        }
    )

    try:
        parser = JsonOutputParser()
        parsed_response = parser.parse(str(response.content))
        wants_visualization = parsed_response.get("wants_visualization", False)

        return {
            "raw_sql_queries_data": raw_sql_queries_data,
            "wants_visualization": wants_visualization,
            "reasoning": parsed_response.get("reasoning", ""),
        }
    except Exception as e:
        logger.error(f"Error parsing check_visualization response: {e}")
        return {
            "raw_sql_queries_data": raw_sql_queries_data,
            "wants_visualization": False,
            "reasoning": "",
        }


def route_next_node(state: State, config: RunnableConfig) -> str:
    wants_visualization = state.get("wants_visualization", False)
    if wants_visualization:
        return "handoff_to_visualizer_agent"
    else:
        return "response"
