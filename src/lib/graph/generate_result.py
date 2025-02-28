import json
from lib.graph.types import AIMessage, ErrorMessage, State, IntermediateStep
from lib.langchain_config import lc
from rich.console import Console

console = Console()

def generate_result(state: State) -> dict:
    """
    Aggregate results of the executed query
    """
    try:
        # Check if we have a "cannot plan further" message
        cannot_plan_further = False
        planning_failure_reason = "Unknown planning failure"

        # Check state for cannot_plan_further flag
        if state.get("cannot_plan_further", False):
            cannot_plan_further = True

            # Try to extract reason from the last message
            if state['messages'] and isinstance(state['messages'][-1], IntermediateStep):
                try:
                    # Ensure content is a string before parsing
                    last_message_content = state['messages'][-1].content
                    if isinstance(last_message_content, str):
                        content = json.loads(last_message_content)
                        if isinstance(content, dict):
                            planning_failure_reason = content.get("reason", planning_failure_reason)
                    elif isinstance(last_message_content, dict):
                        # If content is already a dictionary, use it directly
                        planning_failure_reason = last_message_content.get("reason", planning_failure_reason)
                except (json.JSONDecodeError, AttributeError):
                    pass

        # If planning failed, create a user-friendly response
        if cannot_plan_further:
            explanation_prompt = f"""
                I encountered a problem while trying to answer your query.

                Issue: {planning_failure_reason}

                Please provide a helpful explanation to the user about why their query couldn't be processed,
                and suggest potential alternatives or ways they might rephrase their question.

                Be empathetic and constructive in your response.
            """

            response = lc.llm.invoke(explanation_prompt)
            return {
                "messages": [AIMessage(content=str(response.content))]
            }

        # If we have query results, proceed with normal aggregation
        query_result = state.get("query_result", [])
        last_message = state['messages'][-1]

        # Default response if we can't extract information
        general_response = "I've analyzed your query, but I don't have enough information to provide a detailed answer."

        if not query_result:
            if isinstance(last_message, IntermediateStep):
                try:
                    # Ensure content is a string before parsing
                    message_content = last_message.content
                    if isinstance(message_content, str):
                        content = json.loads(message_content)
                    elif isinstance(message_content, dict):
                        # If content is already a dictionary, use it directly
                        content = message_content
                    else:
                        content = {}

                    if content.get("result") == "Query executed successfully but returned no results":
                        general_response = f"I executed your query successfully, but it returned no results. This might mean that there's no data matching your criteria in the dataset."
                except (json.JSONDecodeError, AttributeError):
                    pass

            return {
                "messages": [AIMessage(content=general_response)]
            }

        # Process query results if available
        query_executed = ""
        if isinstance(last_message, IntermediateStep):
            try:
                # Ensure content is a string before parsing
                message_content = last_message.content
                if isinstance(message_content, str):
                    content = json.loads(message_content)
                elif isinstance(message_content, dict):
                    # If content is already a dictionary, use it directly
                    content = message_content
                else:
                    content = {}

                query_executed = content.get("query_executed", "")
            except (json.JSONDecodeError, AttributeError):
                pass

        # Construct prompt for aggregating results
        user_query = state.get("user_query", "")

        prompt = f"""
            Given the following:
            - Original user query: "{user_query}"
            - SQL query that was executed: "{query_executed}"
            - Query results: {json.dumps(query_result, indent=2)}

            Please provide a concise, clear response that answers the original user query based on these results.
            Include relevant numbers and insights, but avoid unnecessary technical details about the SQL query.
            If the results are extensive, summarize the key findings.
        """

        response = lc.llm.invoke(prompt)
        return {
            "messages": [AIMessage(content=str(response.content))]
        }

    except Exception as e:
        return {
            "messages": [AIMessage(content=f"I encountered an issue while processing your query results. Error: {str(e)}")]
        }