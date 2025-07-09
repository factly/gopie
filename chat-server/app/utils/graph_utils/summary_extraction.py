import statistics
from typing import Any

from langsmith import traceable


@traceable(run_type="tool", name="create_result_summary")
def create_result_summary(result: Any):
    summary = {"type": "sql_query_summary"}

    if isinstance(result, list):
        summary.update(summarize_list_result(result))
    elif isinstance(result, dict):
        summary.update(summarize_dict_result(result))
    elif result is None:
        summary["result_type"] = "null"
    else:
        summary["result_type"] = type(result).__name__
        content = str(result)
        if len(content) > 1000:
            content = content[:1000] + "... (truncated)"
        summary["content"] = content

    return summary


@traceable(run_type="tool", name="summarize_list_result")
def summarize_list_result(result: list):
    summary: Any = {
        "result_type": "list",
        "total_records": str(len(result)),
    }

    if not result:
        return summary

    if isinstance(result[0], dict):
        columns = list(result[0].keys())
        summary["columns"] = columns

        numeric_stats = get_numeric_statistics(result, columns)
        if numeric_stats:
            summary["numeric_statistics"] = numeric_stats

        categorical_stats = get_categorical_statistics(result, columns)
        if categorical_stats:
            summary["categorical_statistics"] = categorical_stats

    summary["sample_data"] = get_sample_data(result)

    if len(result) > 5:
        summary["additional_rows_count"] = str(len(result) - 5)

    return summary


@traceable(run_type="tool", name="summarize_dict_result")
def summarize_dict_result(result: dict):
    keys = list(result.keys())
    summary: Any = {
        "result_type": "dict",
        "total_keys": str(len(keys)),
    }

    sample_keys = {}
    for key in sorted(keys[:20]):
        value = result[key]
        value_str = str(value)
        if len(value_str) > 50:
            value_str = value_str[:47] + "..."

        sample_keys[key] = {
            "type": type(value).__name__,
            "value": value_str,
        }

    summary["sample_keys"] = sample_keys

    if len(keys) > 20:
        summary["additional_keys_count"] = str(len(keys) - 20)

    return summary


@traceable(run_type="tool", name="get_sample_data")
def get_sample_data(result: list) -> list[dict[str, str] | str]:
    samples = []

    for row in result[:5]:
        if isinstance(row, dict):
            sample_row = {}
            for k, v in list(row.items())[:8]:
                sample_row[k] = str(v) if v is not None else None

            if len(row) > 8:
                sample_row["additional_fields_count"] = str(len(row) - 8)

            samples.append(sample_row)
        else:
            samples.append(str(row))

    return samples


@traceable(run_type="tool", name="get_numeric_statistics")
def get_numeric_statistics(
    data: list[dict], columns: list[str]
) -> dict[str, dict[str, str]]:
    """Extract statistical insights from numeric columns"""
    insights = {}

    for col in columns:
        numeric_values = []
        for row in data[:100]:
            if col in row and row[col] is not None:
                try:
                    numeric_values.append(float(row[col]))
                except (ValueError, TypeError):
                    pass

        if len(numeric_values) >= 5:
            try:
                insights[col] = {
                    "min": str(round(min(numeric_values), 2)),
                    "max": str(round(max(numeric_values), 2)),
                    "avg": str(
                        round(sum(numeric_values) / len(numeric_values), 2)
                    ),
                    "median": str(round(statistics.median(numeric_values), 2)),
                }
            except Exception:
                pass

    return insights


@traceable(run_type="tool", name="get_categorical_statistics")
def get_categorical_statistics(
    data: list[dict], columns: list[str]
) -> dict[str, list[dict[str, str]]]:
    insights = {}

    for col in columns:
        value_counts = {}
        total_values = 0

        for row in data[:100]:
            if col in row and row[col] is not None:
                if isinstance(row[col], (str, bool, int)) and not isinstance(
                    row[col], float
                ):
                    value_counts[row[col]] = value_counts.get(row[col], 0) + 1
                    total_values += 1

        if 1 < len(value_counts) < 10 and total_values > 0:
            top_values = sorted(
                value_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]
            column_insights = []

            for val, count in top_values:
                percentage = (count / total_values) * 100
                column_insights.append(
                    {
                        "value": str(val),
                        "count": str(count),
                        "percentage": str(round(percentage, 1)),
                    }
                )

            insights[col] = column_insights

    return insights
