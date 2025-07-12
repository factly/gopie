from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.schema import DatasetSchema
from app.workflow.graph.single_dataset_graph.types import (
    SingleDatasetQueryResult,
    ValidationResult,
)
from app.workflow.prompts.formatters.single_query_result import (
    format_single_query_result,
)


def create_process_query_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are a DuckDB and data expert. Analyze the user's
question and determine if you need to generate SQL queries to get new data or
if you can answer using available context.

INSTRUCTIONS:
1. If the user's question can be answered using the sample data or previous
   context, generate a response with empty SQL queries and give response for
   non-sql queries.
2. If new data analysis is needed, generate appropriate SQL queries

RULES FOR SQL QUERIES (when needed):
- No semicolon at end of query
- Use double quotes for table/column names, single quotes for values
- Exclude rows with state='All India' when filtering/aggregating by state
- For share/percentage calculations, calculate as: (value/total)*100
- Exclude 'Total' category from categorical field calculations
- Include units/unit column when displaying value columns
- Use Levenshtein for fuzzy string matching
- Use ILIKE for case-insensitive matching
- Generate only read queries (SELECT)
- Pay careful attention to exact column names from the schema
- Use the TABLE NAME provided in the input for forming SQL queries

RESPONSE FORMAT:
Return a JSON object in one of these formats:
{
    "sql_queries": ["<SQL query here without semicolon>", ...],
    "explanations": ["<Brief explanation for each query>", ...],
    "response_for_non_sql": "<Brief explanation for non-sql response>"
}

Always respond with valid JSON only."""

    human_template_str = """
{input}
"""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(input=input_content)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]


def format_process_query_input(
    user_query: str,
    dataset_name: str,
    dataset_schema: DatasetSchema,
    rows_csv: str,
    prev_query_result: SingleDatasetQueryResult | None = None,
    validation_result: ValidationResult | None = None,
    **kwargs,
) -> dict:
    formatted_schema = dataset_schema.format_for_prompt()

    input_str = f"""❓ USER QUERY: {user_query}

📊 DATASET INFORMATION:
{formatted_schema}

📄 SAMPLE DATA ({dataset_name}):
{rows_csv}"""

    if prev_query_result:
        formatted_prev_result = format_single_query_result(prev_query_result)
        input_str += f"\n\n🔄 PREVIOUS QUERY CONTEXT:\n{formatted_prev_result}"

    if validation_result:
        confidence = validation_result["confidence"]
        if confidence >= 0.9:
            confidence_desc = "Very high confidence"
            confidence_meaning = "excellent results"
        elif confidence >= 0.7:
            confidence_desc = "High confidence"
            confidence_meaning = "good results, minor improvements possible"
        elif confidence >= 0.4:
            confidence_desc = "Medium confidence"
            confidence_meaning = "some issues, improvements recommended"
        else:  # 0.0-0.3
            confidence_desc = "Low confidence"
            confidence_meaning = "major issues, significant improvements needed"

        validation_status = "✅ Valid" if validation_result["is_valid"] else "❌ Needs Improvement"

        context_note = (
            "📋 ANALYSIS: After reviewing the previous query result above"
            if prev_query_result
            else "📋 ANALYSIS: Initial validation"
        )

        input_str += f"""

{context_note}
🔍 VALIDATION: {validation_status}
📊 Confidence: {confidence:.2f}/1.0 ({confidence_desc} - {confidence_meaning})
💭 Reasoning: {validation_result['reasoning']}
⚠️  The previous query result requires improvements before providing a final response."""

        missing_elements = validation_result["missing_elements"]
        if missing_elements:
            input_str += f"\n❓ Still Missing: {', '.join(missing_elements)}"

    return {"input": input_str}
