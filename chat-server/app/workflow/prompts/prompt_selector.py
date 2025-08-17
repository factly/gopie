from typing import Literal

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable

from .multi_dataset_prompts.analyze_query_prompt import (
    create_analyze_query_prompt,
)
from .multi_dataset_prompts.generate_subqueries_prompt import (
    create_assess_query_complexity_prompt,
    create_generate_subqueries_prompt,
)
from .multi_dataset_prompts.identify_datasets_prompt import (
    create_identify_datasets_prompt,
    format_identify_datasets_input,
)
from .multi_dataset_prompts.plan_query_prompt import (
    create_plan_query_prompt,
    format_plan_query_input,
)
from .multi_dataset_prompts.stream_updates_prompt import (
    create_stream_update_prompt,
)
from .plan_sql_query_tool import (
    create_sql_planning_prompt,
    format_sql_planning_input,
)
from .process_context_prompt import create_process_context_prompt
from .result_generation_prompt import (
    create_result_generation_prompt,
    format_result_generation_input,
)
from .single_dataset_prompts.process_query_prompt import (
    create_process_query_prompt,
    format_process_query_input,
)
from .single_dataset_prompts.validate_result_prompt import (
    create_validate_result_prompt,
    format_validate_result_input,
)
from .validate_input_prompt import create_validate_input_prompt
from .visualiser_agent_prompts.visualize_data_prompt import (
    create_visualize_data_prompt,
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
    "process_context",
    "plan_sql_query_tool",
    "validate_input",
    "validate_result",
    "visualize_data",
]


class PromptSelector:
    def __init__(self):
        """
        Initialize the PromptSelector with mappings for prompt creation and input formatting functions.

        Sets up dictionaries that associate node names with their corresponding prompt generation and input formatting functions, enabling dynamic retrieval and formatting of prompts for various query processing tasks.
        """
        self.prompt_map = {
            "plan_query": create_plan_query_prompt,
            "identify_datasets": create_identify_datasets_prompt,
            "analyze_query": create_analyze_query_prompt,
            "generate_subqueries": create_generate_subqueries_prompt,
            "assess_query_complexity": create_assess_query_complexity_prompt,
            "stream_updates": create_stream_update_prompt,
            "process_query": create_process_query_prompt,
            "generate_result": create_result_generation_prompt,
            "process_context": create_process_context_prompt,
            "plan_sql_query_tool": create_sql_planning_prompt,
            "validate_input": create_validate_input_prompt,
            "validate_result": create_validate_result_prompt,
            "visualize_data": create_visualize_data_prompt,
        }

        self.format_prompt_input_map = {
            "generate_result": format_result_generation_input,
            "identify_datasets": format_identify_datasets_input,
            "plan_query": format_plan_query_input,
            "process_query": format_process_query_input,
            "plan_sql_query_tool": format_sql_planning_input,
            "validate_result": format_validate_result_input,
        }

    def get_prompt_template(self, node_name: str) -> ChatPromptTemplate:
        if node_name not in self.prompt_map:
            raise ValueError(f"No prompt available for node: {node_name}")

        return self.prompt_map[node_name](prompt_template=True)

    def get_prompt(self, node_name: NodeName, **kwargs) -> list[BaseMessage]:
        if node_name not in self.prompt_map:
            raise ValueError(f"No prompt available for node: {node_name}")

        formatted_input = self.format_prompt_input(node_name=node_name, **kwargs)

        if formatted_input:
            return self.prompt_map[node_name](**formatted_input)
        else:
            return self.prompt_map[node_name](**kwargs)

    @traceable
    def format_prompt_input(self, node_name: NodeName, **kwargs) -> dict | None:
        if node_name not in self.format_prompt_input_map:
            return None

        return self.format_prompt_input_map[node_name](**kwargs)
