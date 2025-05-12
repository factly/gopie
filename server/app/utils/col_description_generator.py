import logging

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.langchain_config import lc
from app.models.schema import DatasetSchema


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
    column, generate a brief description (1-2 sentences) that explains
    what the column represents, its data type, and any notable
    characteristics based on the statistics provided.

    dataset_schema: {dataset_schema}

    INSTRUCTIONS:
    1. Generate a concise, informative description for each column
    2. Include the data type and range/distribution information when relevant
    3. Make each description clear and useful for someone analyzing this data
    4. Focus on what the column represents in business/domain terms
    5. Keep descriptions to 1-2 sentences maximum

    Return your response as a JSON object with column names as keys and
    descriptions as values.
    Example format:
    {example_format}
    """

    prompt = ChatPromptTemplate.from_template(template)

    try:
        chain = prompt | lc.llm | JsonOutputParser()
        response = await chain.ainvoke(
            {"dataset_schema": schema, "example_format": example_format}
        )

        return response
    except Exception as e:
        logging.error(f"Error generating column descriptions: {e}")
        return {}
