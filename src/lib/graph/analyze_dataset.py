import json

from src.lib.graph.types import ErrorMessage, IntermediateStep, State
from src.utils.correct_column_values import correct_column_values

# def create_analysis_prompt(
#     user_query: str, column_requirements: list, tools_results: dict
# ) -> str:
#     """Create a prompt for the LLM to analyze the column requirements and plan data gathering"""
#     return f"""
#     You are an experienced data analyst tasked with gathering the necessary information to create an accurate SQL query.

#     USER QUERY:
#     "{user_query}"

#     PRELIMINARY COLUMN REQUIREMENTS (these are initial assumptions and may not be correct):
#     {column_requirements}

#     TOOLS RESULTS (Analyze this and decide whether to use the tools to gather more information or not):
#     {json.dumps(tools_results)}

#     Important: The column requirements above were identified by a preliminary analysis and should be treated as hypotheses, not facts. They might be incomplete, inaccurate, or misaligned with the actual data structure.

#     As a human analyst would do, please:
#      - Analyze the preliminary column requirements critically
#      - Identify what specific information you need to verify or correct these assumptions
#      - Plan how to gather and validate this information systematically
#      - use the appropriate tools to gather the necessary information about the column values

#     If there is a need of calling a tool to answer the query, please call the tool(s) and dont return in the requested format and directly make a tool call

#     Respond in this JSON format:
#     {{
#         "analysis": "Your critical evaluation of the preliminary column requirements, highlighting potential inaccuracies",
#         "data_gathering_plan": "Your plan to gather the necessary information to verify or correct the column requirements",
#         "correct_column_requirements": [
#             {{
#                 "dataset": "dataset_name",
#                 "column_values_that_can_be_used_for_query_generation": ["column1", "column2"],
#             }}
#         ]
#     }}
#     """


def analyze_dataset(state: State) -> dict:
    """
    Analyze the dataset structure and prepare for query planning.
    This function mimics how a human analyst would approach the problem:
        - Critically analyze the requirements
        - Gather the information systematically using appropriate tools
    """
    try:
        query_result = state.get("query_result", {})
        dataset_info = state.get("dataset_info", {})

        column_requirements = dataset_info.get("column_assumptions", [])
        corrected_column_requirements = correct_column_values(column_requirements)

        dataset_info["correct_column_requirements"] = corrected_column_requirements
        dataset_info.pop("column_assumptions", None)

        return {
            "dataset_info": dataset_info,
            "messages": [
                IntermediateStep.from_text(
                    json.dumps(corrected_column_requirements, indent=2)
                )
            ],
        }
    except Exception as e:
        error_msg = f"Dataset analysis failed: {str(e)}"

        query_result = state.get("query_result", {})
        if hasattr(query_result, "add_error_message"):
            query_result.add_error_message(str(e), "Dataset analysis failed")

        return {
            "messages": [ErrorMessage.from_text(json.dumps(error_msg, indent=2))],
            "query_result": query_result,
        }


# def route_from_dataset_analysis(state: State) -> str:
#     """Route to the next node based on analysis results"""
# last_message = state["messages"][-1]

# if has_tool_calls(last_message):
#     return "analytic_tools"

# return "plan_query"
