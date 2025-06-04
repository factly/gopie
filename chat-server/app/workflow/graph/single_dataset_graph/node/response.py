import json
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_model_provider,
)


async def response(state: Any, config: RunnableConfig) -> dict:
    query_result = state.get("query_result")

    if not query_result:
        return {
            "messages": [
                AIMessage(content="I was unable to process your query.")
            ],
            "query_result": query_result,
        }

    user_query = query_result.get("user_query", "")
    dataset_name = query_result.get("dataset_name", "Unknown dataset")
    sql_queries = query_result.get("sql_queries", [])

    successful_results = [r for r in sql_queries if r.get("success", False)]
    failed_results = [r for r in sql_queries if not r.get("success", False)]

    results_context = ""
    if successful_results:
        results_context += "AVAILABLE DATA:\n"
        for i, result in enumerate(successful_results, 1):
            results_context += f"Query {i}: {result.get('explanation', '')}\n"
            if result.get("result"):
                data_preview = json.dumps(result["result"][:10], indent=2)
                results_context += f"Data: {data_preview}\n"
            else:
                results_context += "Data: No results returned\n"
            results_context += "\n"

    guidance_context = ""
    if failed_results:
        guidance_context = """
QUERY LIMITATIONS:
Some aspects of your query could not be processed. This might be due to:
- Data not being available in the expected format
- Specific values or time periods not present in the dataset
- Complex operations that need different approaches

SUGGESTIONS:
- Try rephrasing your question with broader terms
- Ask about general trends rather than specific values
- Consider different time periods or categories that might be available
"""

    custom_prompt = f"""
You are providing a helpful response to a user's data query. Be friendly,
informative, and focus on what CAN be determined from the available data.

USER'S QUESTION: "{user_query}"

DATASET USED: {dataset_name}

{results_context}

{guidance_context}

RESPONSE GUIDELINES:
1. Start with a direct answer to the user's question if data is available
2. Present findings clearly using the actual data provided
3. Use bullet points or numbered lists for multiple pieces of information
4. Format numbers appropriately (use commas, currency symbols,
   percentages as needed)
5. If some data isn't available, focus on what IS available and suggest
   alternative approaches
6. Never mention technical errors, SQL queries, or database issues
7. Don't make up or estimate data that isn't provided
8. Be encouraging and offer constructive next steps if needed
9. Keep the tone conversational and helpful
10. If no data is available, acknowledge this and provide helpful
    suggestions for rephrasing the query

IMPORTANT: Base your response ONLY on the data provided above. Do not add
information that isn't present in the results.
"""

    llm = get_model_provider(config).get_node_llm()

    final_response = await llm.ainvoke(
        {"input": custom_prompt, "chat_history": get_chat_history(config)}
    )

    final_answer = str(final_response.content)

    return {
        "messages": [AIMessage(content=final_answer)],
        "query_result": query_result,
    }
