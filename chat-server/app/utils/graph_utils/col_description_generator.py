from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.models.schema import DatasetSchema
from app.utils.model_registry.model_provider import get_llm_for_other_task

COLUMNS_PROMPT = """
You are a data analyst assistant tasked with generating clear, concise
descriptions for the columns in the dataset.

Below is the schema information for columns in this dataset.
For each column, generate a brief description that explains what the column represents.

dataset_schema: {dataset_schema}

INSTRUCTIONS:
1. Generate a concise description for each column, strictly under 10 words
2. Focus only on what the column represents functionally
3. Do NOT include data types, statistics, or null information

Return your response as a JSON object with column names as keys and descriptions as values.
Example format:
{{
    "column_name_1": "Description of what column_name_1 represents...",
    "column_name_2": "Description of what column_name_2 represents..."
}}
"""


def _get_chain():
    prompt = ChatPromptTemplate.from_template(COLUMNS_PROMPT)
    config = RunnableConfig(
        configurable={
            "metadata": {"type": "col_description_generator"},
        }
    )
    llm = get_llm_for_other_task("generate_col_descriptions", config=config)
    return prompt | llm | JsonOutputParser()


async def generate_column_descriptions(
    schema: DatasetSchema,
) -> dict:
    """
    Generate descriptions for columns in a dataset schema using LLM.

    Args:
        schema: The dataset schema containing column information

    Returns:
        Dictionary mapping column names to their generated descriptions
    """
    try:
        chain = _get_chain()
        response = await chain.ainvoke(
            {
                "dataset_schema": schema.model_dump(exclude_defaults=True),
            }
        )
        logger.info(f"Column descriptions response: {response}")
        if not isinstance(response, dict):
            raise ValueError("Invalid response format")

        return response
    except Exception as e:
        logger.exception(
            f"Error generating column descriptions: {e!s}",
            stack_info=True,
            exc_info=True,
        )
        return {}
