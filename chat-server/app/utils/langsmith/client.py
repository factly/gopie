from langsmith import Client


def get_langsmith_client():
    return Client()


def pull_prompt(prompt_name: str):
    client = get_langsmith_client()
    return client.pull_prompt(prompt_name)


def extract_content_from_prompt_template(prompt_template: str) -> str:
    return str(prompt_template)
