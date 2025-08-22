from app.models.message import ErrorMessage, IntermediateStep
from app.utils.graph_utils.column_value_matching import match_column_values
from app.workflow.graph.multi_dataset_graph.types import State


async def analyze_dataset(state: State) -> dict:
    """
    Analyze the dataset structure and prepare for query planning.
    This function uses SQL queries to verify column values against actual
    database data instead of relying on local files.

    It performs the following checks:
    - Verifies column existence in the datasets
    - Finds exact matches for assumed column values
    - Suggests similar values when exact matches aren't found
    """

    query_result = state["query_result"]
    datasets_info = state["datasets_info"]
    last_message = state["messages"][-1]

    try:
        if isinstance(last_message, ErrorMessage):
            pass

        column_assumptions = datasets_info.get("column_assumptions", [])
        if not column_assumptions:
            raise ValueError("No column assumptions found in the datasets_info.")

        column_mappings = await match_column_values(column_assumptions=column_assumptions)

        datasets_info["correct_column_requirements"] = column_mappings
        datasets_info["column_assumptions"] = None

        message_content = f"""
Here are results from the analysis of the datasets:
{column_mappings.model_dump()}
        """

        return {
            "datasets_info": datasets_info,
            "messages": [IntermediateStep(content=message_content)],
        }

    except Exception as e:
        error_msg = f"Error analyzing dataset: {e!s}"
        query_result.add_error_message(error_msg, "Error analyzing dataset")

        return {
            "query_result": query_result,
            "messages": [ErrorMessage(content=error_msg)],
        }
