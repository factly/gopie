import json
from langchain_core.output_parsers import JsonOutputParser
from src.lib.graph.types import AIMessage, ErrorMessage, State
from src.lib.config.langchain_config import lc

def generate_result(state: State) -> dict:
    """
    Generate results of the executed query for successful cases
    """
    try:
        query_type = state.get("query_type", "")

        if query_type == "conversational" or query_type == "tool_only":
            user_query = state.get("user_query", "")
            Tool_result = state.get("tool_results", [])

            conversational_prompt = f"""
                The user has sent a message: "{user_query}"
                Information that can help you answer the user query in a better way and can actually get them the correct answer, use this infromation to answer the user query, If the information is crucial than don't alter it and show it as it is in a better way: {json.dumps(Tool_result, indent=2)}

                This appears to be a general conversation rather than a data analysis request.
                Please respond naturally to this message as a helpful assistant.
                If it's a greeting, respond with a friendly greeting.
                If it's a question about capabilities, explain what you can do to help with data analysis.
                Keep your response concise and friendly.
            """

            response = lc.llm.invoke(conversational_prompt)
            return {
                "messages": [AIMessage(content=str(response.content))]
            }

        message = state["messages"][-1]
        user_query = state.get("user_query", "")
        query_result = state.get("query_result", [])

        # fallback result
        if not query_result:
            return {
                "messages": [AIMessage(content="I processed your query, but couldn't find any matching data in the available datasets. You might want to try rephrasing your question or asking about different data points.")]
            }

        # Handle successful query with results
        query_executed = ""
        if message:
            try:
                message_content = message.content
                if isinstance(message_content, str):
                    parser = JsonOutputParser()
                    content = parser.parse(message_content)
                elif isinstance(message_content, dict):
                    content = message_content
                else:
                    content = {}

                query_executed = content.get("query_executed", "")
            except Exception as e:
                return {
                    "messages": [ErrorMessage.from_text(json.dumps(f"Could not process query results: {str(e)}"))]
                }

        # Generate a response based on the query results
        prompt = f"""
            Given the following:
            - Original user query: "{user_query}"
            - SQL query that was executed: "{query_executed}"
            - Query results: {json.dumps(query_result, indent=2)}

            Please provide a concise, clear response that answers the original user query based on these results.
            Include relevant numbers and insights from the query results. Format large numbers with commas for readability.
            If the results show financial data, present it clearly with the currency symbol if appropriate.

            IMPORTANT: Make sure to use the exact data from the query results in your response. Do not state that you don't have information when it's present in the query results.
        """

        response = lc.llm.invoke(prompt)
        return {
            "messages": [AIMessage(content=str(response.content))]
        }

    except Exception as e:
        return {
            "messages": [ErrorMessage.from_text(json.dumps(f"Critical error: {str(e)}"))]
        }