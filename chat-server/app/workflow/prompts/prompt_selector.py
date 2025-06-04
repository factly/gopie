from typing import Literal

from app.workflow.prompts.analyze_query_prompt import (
    create_analyze_query_prompt,
)
from app.workflow.prompts.generate_result_prompt import (
    create_conversational_query_prompt,
    create_data_query_prompt,
    create_empty_results_prompt,
)
from app.workflow.prompts.generate_subqueries_prompt import (
    create_assess_query_complexity_prompt,
    create_generate_subqueries_prompt,
)
from app.workflow.prompts.identify_datasets_prompt import (
    create_identify_datasets_prompt,
)
from app.workflow.prompts.plan_query_prompt import create_plan_query_prompt
from app.workflow.prompts.stream_updates_prompt import (
    create_execution_analysis_prompt,
    create_stream_update_prompt,
)

NodeName = Literal[
    "plan_query",
    "identify_datasets",
    "analyze_query",
    "generate_subqueries",
    "assess_query_complexity",
    "system_prompt",
    "conversational_query",
    "data_query",
    "empty_results",
    "stream_updates",
    "execution_analysis",
]


class PromptSelector:
    def __init__(self):
        self.prompt_map = {
            "plan_query": create_plan_query_prompt,
            "identify_datasets": create_identify_datasets_prompt,
            "analyze_query": create_analyze_query_prompt,
            "generate_subqueries": create_generate_subqueries_prompt,
            "assess_query_complexity": create_assess_query_complexity_prompt,
            "conversational_query": create_conversational_query_prompt,
            "data_query": create_data_query_prompt,
            "empty_results": create_empty_results_prompt,
            "stream_updates": create_stream_update_prompt,
            "execution_analysis": create_execution_analysis_prompt,
        }

    def get_prompt(self, node_name: NodeName, **kwargs) -> str:
        """
        Get the appropriate prompt for a workflow node based on the node name.
        """
        if node_name not in self.prompt_map:
            raise ValueError(f"No prompt available for node: {node_name}")

        return self.prompt_map[node_name](**kwargs)
