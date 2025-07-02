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
    try:
        last_message = state["messages"][-1]
        if isinstance(last_message, ErrorMessage):
            pass

        query_result = state.get("query_result", {})
        datasets_info = state.get("datasets_info", {})

        column_assumptions = datasets_info.get("column_assumptions", [])
        if not column_assumptions:
            raise ValueError(
                "No column assumptions found in the datasets_info."
            )

        dataset_name_mapping = datasets_info.get("dataset_name_mapping", {})
        column_mappings = await match_column_values(
            column_assumptions, dataset_name_mapping
        )

        datasets_info[
            "correct_column_requirements"
        ] = column_mappings.model_dump()
        datasets_info.pop("column_assumptions", None)

        return {
            "datasets_info": datasets_info,
            "messages": [
                IntermediateStep.from_json(column_mappings.model_dump())
            ],
        }
    except Exception as e:
        error_msg = f"Dataset analysis failed: {str(e)}"

        query_result = state.get("query_result", {})
        if hasattr(query_result, "add_error_message"):
            query_result.add_error_message(str(e), "Dataset analysis failed")

        return {
            "query_result": query_result,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }
