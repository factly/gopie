from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.models.message import IntermediateStep
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node

from ..types import AgentState


@configure_node(
    role="intermediate",
    progress_message="Validating user input...",
)
async def validate_input(state: AgentState, config: RunnableConfig):
    """
    Asynchronously validates the initial user query for malicious content using a language model.

    Analyzes the user's input with an LLM and parses the result to determine if the input is malicious,
    providing reasoning and a user-facing response. Returns a dictionary containing the original query,
    a boolean flag indicating if the input is invalid, and a list of intermediate step messages.
    """
    user_input = state.get("initial_user_query")
    user_response = "Request cannot be processed."

    try:
        prompt_messages = get_prompt(
            "validate_input",
            user_input=user_input,
        )

        model_provider = get_model_provider(config)
        llm = model_provider.get_llm_for_node("validate_input")

        response = await llm.ainvoke(prompt_messages)

        parser = JsonOutputParser()
        validation_result = parser.parse(str(response.content))

        invalid_input = validation_result.get("is_malicious", False)
        reasoning = validation_result.get("reasoning", "No reasoning provided")
        user_response = validation_result.get("response", "Request cannot be processed.")

        if invalid_input:
            print(f"Malicious prompt detected: {reasoning}")

    except Exception as e:
        print(f"Warning: User input validation failed: {e}")
        invalid_input = False

    return {
        "initial_user_query": user_input,
        "invalid_input": invalid_input,
        "messages": [IntermediateStep(content=user_response)],
    }
