from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage


def create_check_visualization_prompt(
    user_query: str, **kwargs
) -> list[BaseMessage]:
    system_message = SystemMessage(
        content="""You are a strict routing supervisor for a data analysis
system. Your job is to determine if the user EXPLICITLY and CLEARLY requested
data visualization.

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
- Trend analysis: "Show trends", "Analyze patterns" (unless explicitly asking
  to visualize)
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

RESPONSE FORMAT:
Respond with JSON:
{
    "wants_visualization": true/false,
    "reasoning": "clear explanation of why you chose true/false"
}"""
    )

    human_message = HumanMessage(content=f"User question: {user_query}")

    return [system_message, human_message]
