from langchain_core.messages import AIMessage


class IntermediateStep(AIMessage):
    """Represents an intermediate step in the processing pipeline"""

    type: str = "intermediate_step"

    @classmethod
    def from_text(cls, text: str) -> "IntermediateStep":
        return cls(content=text)


class ErrorMessage(AIMessage):
    """Represents an error message"""

    type: str = "error_message"

    @classmethod
    def from_text(cls, text: str) -> "ErrorMessage":
        return cls(content=text)
