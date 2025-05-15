import logging

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.models.schema import DatasetSchema
from app.utils.model_provider import ModelProvider


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
    example_format = """
    {
        "column_name_1": "Description of what column_name_1 represents...",
        "column_name_2": "Description of what column_name_2 represents..."
    }
    """

    template = """
    You are a data analyst assistant tasked with generating clear, concise
    descriptions for columns in a dataset.

    Below is the schema information for columns in this dataset. For each
    column, generate a brief description that explains what the column
    represents.

    dataset_schema: {dataset_schema}

    INSTRUCTIONS:
    1. Generate a concise description for each column, strictly under 10 words
    2. Focus only on what the column represents functionally
    3. Do NOT include data types, statistics, or null information

    Return your response as a JSON object with column names as keys and
    descriptions as values.
    Example format:
    {example_format}
    """

    prompt = ChatPromptTemplate.from_template(template)
    model_provider = ModelProvider()

    try:
        chain = prompt | model_provider.get_llm() | JsonOutputParser()
        response = await chain.ainvoke(
            {
                "dataset_schema": schema,
                "example_format": example_format,
            }
        )

        return response
    except Exception as e:
        logging.error(f"Error generating column descriptions: {e}")
        return {}
