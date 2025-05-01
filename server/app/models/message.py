from langchain_core.messages import AIMessage


class IntermediateStep(AIMessage):
    type: str = "intermediate_step"

    @classmethod
    def from_text(cls, text: str) -> "IntermediateStep":
        return cls(content=text)


class ErrorMessage(AIMessage):
    type: str = "error_message"

    @classmethod
    def from_text(cls, text: str) -> "ErrorMessage":
        return cls(content=text)
