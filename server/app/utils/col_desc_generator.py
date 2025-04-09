import json
import logging
from typing import Dict

from app.core.langchain_config import lc
from app.models.schema import DatasetSchema
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate


def generate_column_descriptions(dataset_schema: DatasetSchema) -> dict:
    """
    Generate accurate column descriptions using an LLM based on column metadata.

    Args:
        dataset_schema: DatasetSchema object containing dataset metadata and column information

    Returns:
        Dictionary mapping column names to their descriptions
    """
    try:
        parser = JsonOutputParser()

        dataset_name = dataset_schema["name"]
        column_info = []

        for column in dataset_schema["columns_details"]:
            col_data = {
                "name": column["name"],
                "type": column["type"],
                "sample_values": _format_sample_values(column["sample_values"]),
                "non_null_count": column.get("non_null_count"),
            }
            column_info.append(col_data)

        prompt_template = """
            You are a data expert specialized in understanding dataset schemas. Your task is to generate accurate,
            logical descriptions for database columns that explain what each column represents in business terms.

            Dataset name: {dataset_name}
            Dataset has {row_count} rows and {col_count} columns.

            For each column below, analyze its name, data type, and sample values to infer what information it contains.
            Provide a concise but informative description (1-2 sentences) that would help the llm understand the column's purpose.

            Be specific about what the column represents. For ID columns, explain what entity they identify.
            For date columns, explain what event or timing they track. For numeric columns, explain what quantity they measure.

            Column information:
            {column_info}

            Return ONLY a valid JSON object where keys are the exact column names and values are your descriptions.
            Format:
            {{
                "column_name1": "Description of what this column represents",
                "column_name2": "Description of what this column represents"
            }}
        """

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=[
                "dataset_name",
                "row_count",
                "col_count",
                "column_info",
            ],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        chain = prompt | lc.llm | parser

        try:
            descriptions = chain.invoke(
                {
                    "dataset_name": dataset_name,
                    "row_count": dataset_schema["row_count"],
                    "col_count": dataset_schema["col_count"],
                    "column_info": json.dumps(column_info, indent=2),
                }
            )

            for column in dataset_schema["columns_details"]:
                if column["name"] not in descriptions:
                    descriptions[column["name"]] = (
                        f"Column representing {column['name'].replace('_', ' ').lower()}"
                    )

            return descriptions

        except Exception as e:
            logging.error(f"Error parsing LLM response: {e}")
            return _generate_fallback_descriptions(dataset_schema)

    except ImportError as e:
        logging.error(f"Error: Required LLM configuration not found. {e}")
        return _generate_fallback_descriptions(dataset_schema)
    except Exception as e:
        logging.error(f"Error generating column descriptions with LLM: {e}")
        return _generate_fallback_descriptions(dataset_schema)


def _format_sample_values(values):
    """Format sample values for better LLM readability"""
    if not values:
        return "No samples available"

    sample_limit = 5
    formatted = values[:sample_limit]

    if len(values) > sample_limit:
        return formatted + ["... (truncated)"]

    return formatted


def _generate_fallback_descriptions(dataset_schema: DatasetSchema) -> Dict[str, str]:
    """Simple rule-based fallback if LLM fails"""
    descriptions = {}

    for column in dataset_schema["columns_details"]:
        col_name = column["name"]
        col_type = column["type"]
        descriptions[col_name] = f"{col_name.replace('_', ' ').title()} ({col_type})"

    return descriptions
