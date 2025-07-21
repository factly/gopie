def langsmith_compatible(content: str) -> str:
    return content.replace("{", "{{").replace("}", "}}")
