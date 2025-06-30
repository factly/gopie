from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client

from app.core.config import settings
from app.core.log import logger
from app.workflow.prompts.prompt_selector import PromptSelector


def get_langsmith_client():
    return Client(api_key=settings.LANGSMITH_API_KEY)


def pull_prompt(prompt_name: str):
    client = get_langsmith_client()

    try:
        prompt = client.get_prompt(prompt_name)
        if prompt:
            return client.pull_prompt(prompt_name)
        else:
            return push_and_get_prompt(prompt_name)
    except Exception as e:
        raise e


def push_prompt(prompt_name: str, prompt_template: ChatPromptTemplate):
    client = get_langsmith_client()
    try:
        result = client.push_prompt(
            prompt_identifier=prompt_name, object=prompt_template
        )
        return result
    except Exception as e:
        raise e


def push_and_get_prompt(prompt_name: str):
    prompt_template = PromptSelector().get_prompt_template(prompt_name)
    push_prompt(prompt_name, prompt_template)
    logger.info(f"Pushed prompt '{prompt_name}' to LangSmith")
    return pull_prompt(prompt_name)
