import json
from langchain_core.output_parsers import JsonOutputParser
from lib.graph.types import AIMessage, ErrorMessage, State, IntermediateStep
from lib.langchain_config import lc
from rich.console import Console
from typing import List, Optional, Type, Any

console = Console()

def generate_result(state: State) -> dict:
    """
    Aggregate results of the executed query or handle conversational responses
    """
    try:
        if state.get("conversational", False):
            user_query = state.get("user_query", "")

            conversational_prompt = f"""
                The user has sent a message: "{user_query}"

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

        last_error_message = message if isinstance(message, ErrorMessage) else None

        retry_count = state.get("retry_count", 0)

        # Case 1: Query planning/execution failed even after retries
        if last_error_message and retry_count >= 3:
            error_content = last_error_message.content
            console.print(f"[bold red]Query failed after {retry_count} attempts. Error: {error_content}[/bold red]")

            explanation_prompt = f"""
                I tried several times to process your query but encountered issues.

                Query: "{user_query}"

                Issue: {error_content}

                Please provide a helpful explanation to the user about why their query couldn't be processed,
                and suggest potential alternatives or ways they might rephrase their question.

                Be empathetic and constructive in your response.
            """

            response = lc.llm.invoke(explanation_prompt)
            return {
                "messages": [AIMessage(content=str(response.content))]
            }

        # Case 2: No query results found but execution was successful
        query_result = state.get("query_result", [])
        if not query_result:
            if message:
                try:
                    message_content = message.content
                    if isinstance(message_content, str):
                        try:
                            parser = JsonOutputParser()
                            content = parser.parse(message_content)
                        except:
                            content = {}
                    elif isinstance(message_content, dict):
                        content = message_content
                    else:
                        content = {}

                    if content.get("result") == "Query executed successfully but returned no results":
                        empty_result_prompt = f"""
                            User query: "{user_query}"

                            I executed a query to answer this question, but it returned no results.

                            Provide a helpful response explaining that no matching data was found in the dataset,
                            and suggest possible reasons why (e.g., data might not cover the time period they're asking about,
                            or the specific criteria they mentioned might not exist in our database).

                            Be friendly and offer alternative approaches they could try.
                        """

                        response = lc.llm.invoke(empty_result_prompt)
                        return {
                            "messages": [AIMessage(content=str(response.content))]
                        }
                except Exception as e:
                    console.print(f"[bold yellow]Warning: Error processing intermediate step: {str(e)}[/bold yellow]")

            # Fallback for no results case
            return {
                "messages": [AIMessage(content="I processed your query, but couldn't find any matching data in the available datasets. You might want to try rephrasing your question or asking about different data points.")]
            }

        # Case 3: Successful query with results
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
                console.print(f"[bold yellow]Warning: Could not extract executed query: {str(e)}[/bold yellow]")

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
        console.print(f"[bold red]Critical error in generate_result: {str(e)}[/bold red]")
        return {
            "messages": [AIMessage(content=f"I encountered an issue while processing your query results. Error: {str(e)}")]
        }