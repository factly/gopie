from typing import Literal

from langchain_core.messages import BaseMessage

from app.core.log import logger
from app.workflow.prompts.analyze_query_prompt import (
    create_analyze_query_prompt,
)
from app.workflow.prompts.generate_result_prompt import (
    create_generate_result_prompt,
    format_generate_result_input,
)
from app.workflow.prompts.generate_subqueries_prompt import (
    create_assess_query_complexity_prompt,
    create_generate_subqueries_prompt,
)
from app.workflow.prompts.identify_datasets_prompt import (
    create_identify_datasets_prompt,
    format_identify_datasets_input,
)
from app.workflow.prompts.plan_query_prompt import (
    create_plan_query_prompt,
    format_plan_query_input,
)
from app.workflow.prompts.stream_updates_prompt import (
    create_execution_analysis_prompt,
    create_stream_update_prompt,
)

from ..graph.single_dataset_graph.prompts.check_visualization_prompt import (
    create_check_visualization_prompt,
)
from ..graph.single_dataset_graph.prompts.process_query_prompt import (
    create_process_query_prompt,
    format_process_query_input,
)
from ..graph.single_dataset_graph.prompts.response_prompt import (
    create_response_prompt,
)

NodeName = Literal[
    "plan_query",
    "identify_datasets",
    "analyze_query",
    "generate_subqueries",
    "assess_query_complexity",
    "generate_result",
    "stream_updates",
    "execution_analysis",
    "process_query",
    "response",
    "check_visualization",
]


class PromptSelector:
    def __init__(self):
        self.prompt_map = {
            "plan_query": create_plan_query_prompt,
            "identify_datasets": create_identify_datasets_prompt,
            "analyze_query": create_analyze_query_prompt,
            "generate_subqueries": create_generate_subqueries_prompt,
            "assess_query_complexity": create_assess_query_complexity_prompt,
            "generate_result": create_generate_result_prompt,
            "stream_updates": create_stream_update_prompt,
            "execution_analysis": create_execution_analysis_prompt,
            "process_query": create_process_query_prompt,
            "response": create_response_prompt,
            "check_visualization": create_check_visualization_prompt,
        }

        self.format_prompt_input_map = {
            "generate_result": format_generate_result_input,
            "identify_datasets": format_identify_datasets_input,
            "plan_query": format_plan_query_input,
            "process_query": format_process_query_input,
        }

    def get_prompt(
        self, node_name: NodeName, **kwargs
    ) -> list[BaseMessage] | str:
        if node_name not in self.prompt_map:
            raise ValueError(f"No prompt available for node: {node_name}")

        formatted_input = self.format_prompt_input(node_name, **kwargs)

        if formatted_input:
            return self.prompt_map[node_name](formatted_input["input"])
        else:
            return self.prompt_map[node_name](**kwargs)

    def format_prompt_input(
        self, node_name: NodeName, **kwargs
    ) -> dict | None:
        if node_name not in self.format_prompt_input_map:
            logger.debug(
                f"No format prompt input available for node: {node_name}"
            )
            return None

        return self.format_prompt_input_map[node_name](**kwargs)
