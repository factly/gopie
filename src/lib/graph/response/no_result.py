import json

from src.lib.config.langchain_config import lc
from src.lib.graph.types import AIMessage, ErrorMessage, IntermediateStep, State


def no_results_handler(state: State) -> dict:
    """
    Handle cases where query executed successfully but returned no results
    """
    try:
        user_query = state.get("user_query", "")

        process_info = []
        for message in state["messages"]:
            if isinstance(message, ErrorMessage) or isinstance(
                message, IntermediateStep
            ):
                process_info.append(message.content)

        process_info_text = (
            "\n".join(process_info)
            if process_info
            else "No additional process information available."
        )

        empty_result_prompt = f"""
            User query: "{user_query}"

            I executed a query to answer this question, but it returned no results.

            Technical details about the query processing:
            {process_info_text}

            Provide a helpful response explaining that:
            1. No matching data was found in the dataset
            2. Possible reasons based on the query processing information above
            3. Be specific about why the query might have failed (e.g., time periods not in dataset, entities not found, etc.)

            Suggestions for the user:
            1. Offer 2-3 alternative phrasings they could try
            2. Suggest broader or more general queries that might yield results
            3. Recommend checking for typos or using different terminology

            Be friendly, empathetic, and constructive in your response.
        """

        response = lc.llm.invoke(empty_result_prompt)
        return {"messages": [AIMessage(content=str(response.content))]}
    except Exception as e:
        return {
            "messages": [
                ErrorMessage.from_text(
                    json.dumps(f"Error in no results handler: {str(e)}")
                )
            ]
        }
