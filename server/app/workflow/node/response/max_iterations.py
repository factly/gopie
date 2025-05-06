from app.core.langchain_config import lc
from app.models.message import AIMessage, ErrorMessage
from app.workflow.graph.types import State


async def max_iterations_reached(state: State) -> dict:
    """
    Handle cases where query planning/execution failed after maximum retry
    attempts
    """
    try:
        user_query = state.get("user_query", "")

        error_content = []
        for message in state.get("messages", []):
            if isinstance(message, ErrorMessage):
                error_content.append(message.content[0])

        error_summary = (
            "\n".join(error_content)
            if error_content
            else "An unknown error occurred while processing your query."
        )

        explanation_prompt = f"""
        You're responding to a user whose query has exceeded maximum retry
        attempts.

        User Query: "{user_query}"

        Technical Issues Encountered:
        {error_summary}

        Please:
        1. Explain in simple terms why the query couldn't be processed
        2. Suggest 2-3 specific ways to rephrase or modify their question
        3. Provide alternative approaches if applicable

        Be concise, empathetic and constructive in your response.
        """

        response = await lc.llm.ainvoke(explanation_prompt)
        return {"messages": [AIMessage(content=response.content)]}
    except Exception as e:
        return {
            "messages": [
                ErrorMessage.from_json(
                    {"error": f"Error in max iterations handler: {e!s}"}
                )
            ]
        }
