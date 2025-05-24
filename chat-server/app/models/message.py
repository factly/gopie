from attr import dataclass
from langchain_core.messages import AIMessage


class IntermediateStep(AIMessage):
    type: str = "intermediate_step"

    @classmethod
    def from_text(cls, text: str) -> "IntermediateStep":
        return cls(content=text)

    @classmethod
    def from_json(cls, json_content: dict) -> "IntermediateStep":
        return cls(content=[json_content])


class ErrorMessage(AIMessage):
    type: str = "error_message"

    @classmethod
    def from_text(cls, text: str) -> "ErrorMessage":
        return cls(content=text)

    @classmethod
    def from_json(cls, json_content: dict) -> "ErrorMessage":
        return cls(content=[json_content])


@dataclass
class FinalQueryOutput:
    result: str
    execution_time: float

    def to_dict(self) -> dict:
        return {
            "result": self.result,
            "execution_time": self.execution_time,
        }
