from typing import Literal, Optional, TypedDict, Union

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field, field_validator


class ConfigSchema(TypedDict):
    model_id: str
    trace_id: str
    chat_id: str
    chat_history: list[BaseMessage]
    user: str


PossibleNumberType = Optional[Union[float, int, str]]


def get_possible_number_field():
    return Field(default=None, union_mode="left_to_right")


ColumnFieldsToExclude = Literal["sample_values", "stats", "unique_count", "avg", "count", "std"]


class ColumnSummary(BaseModel):
    column_name: str
    column_type: str
    approx_unique: int
    min: PossibleNumberType = get_possible_number_field()
    max: PossibleNumberType = get_possible_number_field()
    avg: PossibleNumberType = get_possible_number_field()
    std: PossibleNumberType = get_possible_number_field()
    q25: PossibleNumberType = get_possible_number_field()
    q50: PossibleNumberType = get_possible_number_field()
    q75: PossibleNumberType = get_possible_number_field()
    count: int
    null_percentage: dict[str, int]

    @field_validator("min", "max", "avg", "std", "q25", "q50", "q75", mode="before")
    def replace_str_with_none(cls, value):
        if isinstance(value, str) and value == "":
            return None
        return value


class ColumnSchema(ColumnSummary):
    column_description: Optional[str] = None
    sample_values: list[PossibleNumberType] = Field(default_factory=list)

    def format_for_prompt(self, fields_to_exclude: list[ColumnFieldsToExclude] = []):
        sample_str = ""
        stats_info = ""
        unique_count = ""
        if "sample_values" not in fields_to_exclude:
            sample_values = self.sample_values or []
            sample_str = ""
            if sample_values:
                formatted_samples = [str(val) for val in sample_values[:5]]
                sample_str = f" | Sample values: {', '.join(formatted_samples)}"
                if len(sample_values) > 5:
                    sample_str += "..."
        if "stats" not in fields_to_exclude:
            stats_info = ""
            if self.min is not None or self.max is not None:
                min_val = self.min
                max_val = self.max
                if min_val is not None and max_val is not None:
                    stats_info = f" | Range: {min_val} to {max_val}"
                if "avg" not in fields_to_exclude:
                    avg_val = self.avg
                    if avg_val is not None:
                        stats_info += f" | Avg: {avg_val}"
                if "std" not in fields_to_exclude:
                    std_val = self.std
                    if std_val is not None:
                        stats_info += f" | Std: {std_val}"
                if "count" not in fields_to_exclude:
                    count_val = self.count
                    if count_val is not None:
                        stats_info += f" | Count: {count_val}"
        if "unique_count" not in fields_to_exclude:
            unique_count = self.approx_unique
            if unique_count is not None:
                unique_count = f" | ~{unique_count} unique values"
        formatted_str = f"{self.column_name} ({self.column_type})\n"
        formatted_str += f"  Description: {self.column_description}"
        formatted_str += f"{sample_str}{stats_info}{unique_count}"
        return formatted_str


class DatasetSchema(BaseModel):
    name: str
    dataset_name: str
    project_custom_prompt: Optional[str] = None
    dataset_custom_prompt: Optional[str] = None
    dataset_description: str
    project_id: str
    dataset_id: str
    columns: list[ColumnSchema]

    def format_for_prompt(
        self,
        fields_to_exclude: list[Literal["dataset_custom_prompt", "project_custom_prompt"]] = [],
        columns_fields_to_exclude: list[ColumnFieldsToExclude] = [],
    ):
        columns = self.columns or []
        text = f"- Name: {self.name}\n"
        text += f"- Table Name (for SQL): {self.dataset_name}\n"
        text += f"- Description: {self.dataset_description}\n"
        # TODO: Change project_custom_prompt only once per project.
        custom_instructions = ""
        if self.project_custom_prompt and "project_custom_prompt" not in fields_to_exclude:
            custom_instructions += f"{self.project_custom_prompt}\n"
        if self.dataset_custom_prompt and "dataset_custom_prompt" not in fields_to_exclude:
            custom_instructions += f"{self.dataset_custom_prompt}\n"
        if custom_instructions:
            text += f"- Dataset Specific Instructions:\n{custom_instructions}\n"
        text += f"COLUMNS ({len(columns)} total):\n"
        for i, column in enumerate(columns, 1):
            text += f"{i}. {column.format_for_prompt(columns_fields_to_exclude)}\n"
        return text


class DatasetSummary(BaseModel):
    summary: list[ColumnSummary]
