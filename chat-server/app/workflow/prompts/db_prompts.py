"""Database-aware prompt generation utilities.

This module provides database-specific instructions for LLM prompts,
enabling the chat server to generate SQL compatible with different
OLAP backends (DuckDB, ClickHouse).
"""

from app.utils.olap import is_clickhouse_family, is_duckdb_family


def get_db_name() -> str:
    """Get the display name of the current OLAP backend.

    Returns:
        Human-readable database name for use in prompts.
    """
    if is_duckdb_family():
        return "DuckDB"
    elif is_clickhouse_family():
        return "ClickHouse"
    else:
        # Default to DuckDB if unknown
        return "DuckDB"


def get_sql_compatibility_instructions() -> str:
    """Get database-specific SQL compatibility instructions.

    Returns:
        Instructions string for LLM prompts describing SQL dialect rules.
    """
    db_name = get_db_name()

    base_instructions = f"""- SQL queries MUST be compatible with {db_name}
- Use exact dataset_name (table name) from schema, not user-friendly names
- No semicolons at end of queries
- Use double quotes for table/column names, single quotes for values"""

    if is_clickhouse_family():
        return base_instructions + """
- ClickHouse-specific: Use levenshteinDistance() for fuzzy string matching
- ClickHouse-specific: String concatenation uses concat() function
- ClickHouse-specific: Use rand() for random number generation
- ClickHouse-specific: Use match(column, 'pattern') for regex pattern matching"""
    else:
        return base_instructions + """
- DuckDB-specific: Use levenshtein() for fuzzy string matching
- DuckDB-specific: String concatenation uses || operator
- DuckDB-specific: Use random() for random number generation
- DuckDB-specific: Use REGEXP_MATCHES(column, 'pattern') for regex pattern matching"""


def get_expert_role() -> str:
    """Get the database expert role description for prompts.

    Returns:
        Role description string for system prompts.
    """
    db_name = get_db_name()
    return f"You are a {db_name} and data expert."
