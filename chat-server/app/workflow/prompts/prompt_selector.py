from typing import Literal

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable

from .data_planning_prompt import (
    data_planning_prompt,
    format_data_planning_input,
)
from .generate_sql_prompt import format_generate_sql_input, generate_sql_prompt
from .multi_dataset_prompts.analyze_query_prompt import (
    analyze_query_prompt,
    format_analyze_query_input,
)
from .multi_dataset_prompts.generate_subqueries_prompt import (
    generate_subqueries_prompt,
)
from .multi_dataset_prompts.identify_datasets_prompt import (
    format_identify_datasets_input,
    identify_datasets_prompt,
)
from .multi_dataset_prompts.regenerate_fuzzy_values_prompt import (
    format_regenerate_fuzzy_values_input,
    regenerate_fuzzy_values_prompt,
)
from .multi_dataset_prompts.stream_updates_prompt import (
    format_stream_update_input,
    stream_update_prompt,
)
from .multi_dataset_prompts.validate_match_relevance_prompt import (
    validate_match_relevance_prompt,
)
from .process_context_prompt import (
    format_process_context_input,
    process_context_prompt,
)
from .result_generation_prompt import (
    format_result_generation_input,
    result_generation_prompt,
)
from .single_dataset_prompts.extract_column_assumptions_prompt import (
    extract_column_assumptions_prompt,
    format_extract_column_assumptions_input,
)
from .single_dataset_prompts.validate_result_prompt import (
    format_validate_result_input,
    validate_result_prompt,
)
from .validate_input_prompt import validate_input_prompt
from .visualiser_agent_prompts.feedback_prompt import (
    create_feedback_prompt,
    format_feedback_input,
)
from .visualiser_agent_prompts.visualize_data_prompt import (
    format_visualization_input,
    visualize_data_prompt,
)

NodeName = Literal[
    "generate_sql",
    "identify_datasets",
    "analyze_query",
    "generate_subqueries",
    "generate_result",
    "stream_updates",
    "process_context",
    "data_planning",
    "validate_input",
    "validate_result",
    "visualize_data",
    "regenerate_fuzzy_values",
    "validate_match_relevance",
    "feedback",
    "extract_column_assumptions",
]


class PromptSelector:
    def __init__(self):
        """
        Sets up dictionaries that associate node names with their corresponding prompt generation and input formatting functions, enabling dynamic retrieval and formatting of prompts for various query processing tasks.
        """

        self.prompt_map = {
            "identify_datasets": identify_datasets_prompt,
            "analyze_query": analyze_query_prompt,
            "generate_subqueries": generate_subqueries_prompt,
            "stream_updates": stream_update_prompt,
            "generate_result": result_generation_prompt,
            "process_context": process_context_prompt,
            "data_planning": data_planning_prompt,
            "generate_sql": generate_sql_prompt,
            "validate_input": validate_input_prompt,
            "validate_result": validate_result_prompt,
            "visualize_data": visualize_data_prompt,
            "regenerate_fuzzy_values": regenerate_fuzzy_values_prompt,
            "validate_match_relevance": validate_match_relevance_prompt,
            "feedback": create_feedback_prompt,
            "extract_column_assumptions": extract_column_assumptions_prompt,
        }

        self.format_prompt_input_map = {
            "analyze_query": format_analyze_query_input,
            "generate_result": format_result_generation_input,
            "identify_datasets": format_identify_datasets_input,
            "generate_sql": format_generate_sql_input,
            "stream_updates": format_stream_update_input,
            "validate_result": format_validate_result_input,
            "visualize_data": format_visualization_input,
            "process_context": format_process_context_input,
            "data_planning": format_data_planning_input,
            "regenerate_fuzzy_values": format_regenerate_fuzzy_values_input,
            "feedback": format_feedback_input,
            "extract_column_assumptions": format_extract_column_assumptions_input,
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

    def format_prompt_input(self, node_name: NodeName, **kwargs) -> dict | None:
        if node_name not in self.format_prompt_input_map:
            return None

        @traceable
        def format_input(node_name: NodeName, **kwargs):
            return self.format_prompt_input_map[node_name](**kwargs)

        return format_input(node_name=node_name, **kwargs)
