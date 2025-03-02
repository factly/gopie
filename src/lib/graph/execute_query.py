import json
from langchain_core.output_parsers import JsonOutputParser
import os
import re
import duckdb
import pandas as pd
from lib.graph.types import ErrorMessage, State, IntermediateStep
from typing import Dict, Any
import logging

NUMERIC_KEYWORDS = ['amount', 'cost', 'value', 'spent', 'outlay']
MAX_RETRY_COUNT = 3

def get_data_directory() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data')

def normalize_name(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', os.path.splitext(name)[0]).lower()

def validate_and_fix_query(query: str) -> str:
    """
    Validate and fix common SQL query issues

    Args:
        query: The SQL query string to validate and fix

    Returns:
        A corrected SQL query string
    """
    # Remove any trailing commas before clauses
    query = re.sub(r',\s*(?=FROM|WHERE|GROUP|ORDER|HAVING|LIMIT)', ' ', query, flags=re.IGNORECASE)
    query = ' '.join(query.split())
    query = re.sub(r'([^".])(FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                  lambda m: f'{m.group(1)}{m.group(2)} "{m.group(3)}"',
                  query,
                  flags=re.IGNORECASE)

    if 'GROUP BY' in query.upper() and 'AS' in query.upper():
        parts = query.split('GROUP BY', 1)
        select_part = parts[0]
        group_by_part = parts[1]

        aliases = {}
        for match in re.finditer(r'(\w+)\s+AS\s+(\w+)', select_part, re.IGNORECASE):
            aliases[match.group(2)] = match.group(1)

        for alias, col in aliases.items():
            group_by_part = re.sub(rf'\b{alias}\b', col, group_by_part)

        query = f"{select_part} GROUP BY {group_by_part}"

    query = re.sub(r'(JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                  lambda m: f'{m.group(1)} "{m.group(2)}"',
                  query,
                  flags=re.IGNORECASE)

    location_columns = ['district', 'state', 'city', 'sector', 'csr_project_name', 'implementation_mode']
    for col in location_columns:
        query = re.sub(rf'(["\s]){col}(["\s]*)\s*=\s*\'([^\']+)\'',
                        rf'\1{col}\2 ILIKE \'\3\'',
                        query,
                        flags=re.IGNORECASE)

        query = re.sub(rf'(["\s]){col}(["\s]*)\s+LIKE\s+\'([^\']+)\'',
                        rf'\1{col}\2 ILIKE \'\3\'',
                        query,
                        flags=re.IGNORECASE)

        in_clause_pattern = rf'(["\s]){col}(["\s]*)\s+IN\s+\(([^\)]+)\)'
        if re.search(in_clause_pattern, query, re.IGNORECASE):
            matches = re.finditer(in_clause_pattern, query, re.IGNORECASE)
            for match in matches:
                full_match = match.group(0)
                col_prefix = match.group(1)
                col_suffix = match.group(2)
                values = match.group(3)

                values_list = [v.strip().strip("'\"") for v in values.split(',')]

                ilike_conditions = []
                for value in values_list:
                    if value.strip():
                        ilike_conditions.append(f"{col_prefix}{col}{col_suffix} ILIKE '{value}'")

                if ilike_conditions:
                    replacement = "(" + " OR ".join(ilike_conditions) + ")"
                    query = query.replace(full_match, replacement)

    return query

def safe_json_parse(content: str) -> Dict[str, Any]:
    """
    Safely parse JSON content with error handling

    Args:
        content: JSON string to parse

    Returns:
        Parsed JSON as a dictionary
    """
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        return {}

def execute_query(state: State) -> dict:
    """
    Execute the planned query

    Args:
        state: The current state object containing messages and query information

    Returns:
        Updated state with query results or error messages
    """
    con = None
    try:
        last_message = state['messages'][-1]
        content = last_message.content if isinstance(last_message.content, str) else json.dumps(last_message.content)

        query_plan = None
        try:
            parser = JsonOutputParser()
            query_plan = parser.parse(content)
        except Exception:
            query_plan = safe_json_parse(content)

        if not query_plan:
            raise ValueError("Failed to parse query plan from message")

        if not query_plan.get('selected_dataset') and query_plan.get('tables_used'):
            query_plan['selected_dataset'] = query_plan['tables_used'][0]

        con = duckdb.connect(database=':memory:')
        data_dir = get_data_directory()

        dataset_name = query_plan.get('selected_dataset', '')
        if not dataset_name:
            sql_query = query_plan.get('sql_query', '')
            if 'FROM' in sql_query.upper():
                match = re.search(r'FROM\s+([^\s,;()]+)', sql_query, re.IGNORECASE)
                if match:
                    dataset_name = match.group(1).strip('"\'')
                    dataset_name = dataset_name.split('WHERE')[0].strip() if 'WHERE' in dataset_name else dataset_name

        if not dataset_name:
            raise ValueError("No dataset specified in query plan")

        dataset_name = dataset_name.replace('.csv', '')
        matching_files = [f for f in os.listdir(data_dir)
                        if f.endswith('.csv') and dataset_name.lower() in f.lower()]

        if not matching_files:
            raise FileNotFoundError(f"Dataset not found: {dataset_name}")

        file_path = os.path.join(data_dir, matching_files[0])
        table_name = normalize_name(matching_files[0])

        df = pd.read_csv(file_path)

        for col in df.columns:
            if df[col].dtype == 'object':
                df[f"{col.lower()}_lower"] = df[col].str.lower()

        original_cols = df.columns
        clean_cols = {col: col.lower().strip().replace(' ', '_') for col in original_cols}
        df.rename(columns=clean_cols, inplace=True)

        for col in df.columns:
            if any(term in col.lower() for term in NUMERIC_KEYWORDS):
                try:
                    df[col] = pd.to_numeric(
                        df[col].astype(str).str.replace(r'[$,]', '', regex=True),
                        errors='coerce'
                    ).fillna(0)
                except Exception as e:
                    logging.warning(f"Failed to convert column '{col}' to numeric: {str(e)}")

        try:
            con.execute(f"DROP TABLE IF EXISTS \"{table_name}\"")
            con.execute(f"CREATE TABLE \"{table_name}\" AS SELECT * FROM df")
        except Exception as e:
            raise ValueError(f"Failed to create table in DuckDB: {str(e)}")

        sql_query = query_plan.get('sql_query') or query_plan.get('sample_query')
        if not sql_query:
            raise ValueError("No SQL query found in plan")

        sql_query = sql_query.replace(dataset_name, f'"{table_name}"')

        result = None
        try:
            result = con.execute(sql_query).fetchdf()
        except Exception as original_error:
            try:
                fixed_query = validate_and_fix_query(sql_query)
                result = con.execute(fixed_query).fetchdf()
                sql_query = fixed_query
            except Exception as fixed_error:
                raise ValueError(f"Query execution failed. Original error: {str(original_error)}. "
                                f"After fixing: {str(fixed_error)}")

        if result.empty:
            no_results_data = {
                "result": "Query executed successfully but returned no results",
                "query_executed": sql_query,
                "data": [],
                "formatted_data": []
            }
            return {
                "messages": [ErrorMessage.from_text(json.dumps(no_results_data, indent=2))]
            }

        for col in result.select_dtypes(include=['float64', 'int64']).columns:
            result[col] = result[col].fillna(0)

        numeric_cols = result.select_dtypes(include=['float64', 'int64']).columns
        formatted_result = result.copy()
        for col in numeric_cols:
            if any(keyword in col.lower() for keyword in NUMERIC_KEYWORDS):
                formatted_result[f"{col}_formatted"] = formatted_result[col].apply(
                    lambda x: f"₹{x:,.2f}" if x >= 1 else f"₹{x:.2f}"
                )

        result_records = result.to_dict('records')
        formatted_records = formatted_result.to_dict('records')

        result_dict = {
            "result": "Query executed successfully",
            "query_executed": sql_query,
            "data": result_records,
            "formatted_data": formatted_records
        }

        return {
            "query_result": result_records,
            "messages": [IntermediateStep.from_text(json.dumps(result_dict, indent=2))]
        }

    except Exception as e:
        error_msg = f"Query execution error: {str(e)}"
        return {
            "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))]
        }

    finally:
        if con:
            con.close()

def route_query_replan(state: State) -> str:
    """
    Determine whether to replan the query or generate results based on execution status

    Args:
        state: The current state containing messages and retry information

    Returns:
        Routing decision: "replan" or "generate_result"
    """
    last_message = state['messages'][-1]
    content = ""

    if isinstance(last_message.content, str):
        content = last_message.content
    elif isinstance(last_message.content, dict):
        content = json.dumps(last_message.content)

    has_error = False
    try:
        parsed_content = safe_json_parse(content)
        has_error = "error" in parsed_content and parsed_content["error"]
    except:
        has_error = False

    is_error_message = isinstance(last_message, ErrorMessage)
    retry_count = state.get('retry_count', 0)

    if (has_error or is_error_message) and retry_count < MAX_RETRY_COUNT:
        state['retry_count'] = retry_count + 1
        return "replan"

    return "generate_result"
