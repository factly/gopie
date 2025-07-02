from langsmith import Client

from app.core.config import settings


def get_langsmith_client():
    return Client(api_key=settings.LANGSMITH_API_KEY)


def pull_prompt(prompt_name: str):
    client = get_langsmith_client()
    return client.pull_prompt(prompt_name)
