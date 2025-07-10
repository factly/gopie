from langsmith import traceable

from app.models.query import ResultSummary
from app.utils.graph_utils.result_validation import truncate_result_for_llm


@traceable(run_type="tool", name="create_result_summary")
def create_result_summary(result: list) -> ResultSummary:
    if isinstance(result, list):
        truncated_result = truncate_result_for_llm(result)
        return ResultSummary(
            total_records=str(len(result)),
            truncated_data=truncated_result,
            note=(
                f"This result was large ({len(result)} rows) and has been "
                f"summarized. Complete data is available separately."
            ),
        )
