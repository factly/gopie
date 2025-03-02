import json
from langchain_core.output_parsers import JsonOutputParser
import os
import re
import duckdb
import pandas as pd
from lib.graph.types import ErrorMessage, State, IntermediateStep

def get_data_directory() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data')

def normalize_name(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', os.path.splitext(name)[0]).lower()

def validate_and_fix_query(query: str) -> str:
    """
    Validate and fix common SQL query issues
    """
    # Remove any trailing commas
    query = re.sub(r',\s*(?=FROM|WHERE|GROUP|ORDER|HAVING|LIMIT)', ' ', query)

    # Remove any trailing/leading whitespace and ensure single spaces
    query = ' '.join(query.split())

    # Ensure proper quoting of identifiers
    query = re.sub(r'([^".])(FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)', r'\1\2 "\3"', query)

    # Fix common GROUP BY issues
    if 'GROUP BY' in query.upper() and 'AS' in query.upper():
        # Remove aliases from GROUP BY
        parts = query.split('GROUP BY')
        select_part = parts[0]
        group_by_part = parts[1]

        # Extract column aliases
        aliases = {}
        for match in re.finditer(r'(\w+)\s+AS\s+(\w+)', select_part, re.IGNORECASE):
            aliases[match.group(2)] = match.group(1)

        # Replace aliases in GROUP BY with original column names
        for alias, col in aliases.items():
            group_by_part = re.sub(rf'\b{alias}\b', col, group_by_part)

        query = f"{select_part} GROUP BY {group_by_part}"

    return query

def execute_query(state: State) -> dict:
    """Execute the planned query"""
    con = None
    try:
        # Parse the last message for query plan using JSONOutputParser
        last_message = state['messages'][-1]
        content = last_message.content if isinstance(last_message.content, str) else json.dumps(last_message.content)

        # Use LangChain's JsonOutputParser instead of manual parsing
        parser = JsonOutputParser()
        try:
            query_plan = parser.parse(content)
        except Exception:
            # Fallback to manual parsing if JSONOutputParser fails
            query_plan = json.loads(content)

        # If no selected_dataset but tables_used exists, use the first table
        if not query_plan.get('selected_dataset') and query_plan.get('tables_used'):
            query_plan['selected_dataset'] = query_plan['tables_used'][0]

        con = duckdb.connect(database=':memory:')
        data_dir = get_data_directory()

        dataset_name = query_plan.get('selected_dataset', '')
        if not dataset_name:
            # Try to extract dataset name from SQL query
            sql_query = query_plan.get('sql_query', '')
            if 'FROM' in sql_query.upper():
                dataset_name = sql_query.upper().split('FROM')[1].split()[0].strip()
                dataset_name = dataset_name.split('WHERE')[0].strip() if 'WHERE' in dataset_name else dataset_name

        if not dataset_name:
            raise ValueError("No dataset specified in query plan")

        dataset_name = dataset_name.replace('.csv', '')

        matching_files = [f for f in os.listdir(data_dir)
                        if f.endswith('.csv') and dataset_name.lower() in f.lower()]

        if not matching_files:
            raise FileNotFoundError(f"Dataset not found: {dataset_name}")

        file_path = os.path.join(data_dir, matching_files[0])

        table_name = os.path.splitext(matching_files[0])[0].lower()
        table_name = re.sub(r'[^a-zA-Z0-9_]', '_', table_name)

        df = pd.read_csv(file_path)

        original_cols = df.columns
        clean_cols = {col: col.lower().strip().replace(' ', '_') for col in original_cols}
        df.rename(columns=clean_cols, inplace=True)

        for col in df.columns:
            if any(term in col.lower() for term in ['amount', 'outlay', 'spent', 'cost', 'value']):
                try:
                    df[col] = pd.to_numeric(
                        df[col].astype(str).str.replace(r'[$,]', '', regex=True),
                        errors='coerce'
                    ).fillna(0)
                except Exception as e:
                    raise ValueError(f"Failed to convert column '{col}' to numeric: {str(e)}")

        try:
            con.execute(f"DROP TABLE IF EXISTS \"{table_name}\"")
            con.execute(f"CREATE TABLE \"{table_name}\" AS SELECT * FROM df")
        except Exception as e:
            raise ValueError(f"Failed to create table: {str(e)}")

        sql_query = query_plan.get('sql_query') or query_plan.get('sample_query')
        if not sql_query:
            raise ValueError("No SQL query found in plan")

        sql_query = sql_query.replace(dataset_name, f'"{table_name}"')

        try:
            result = con.execute(sql_query).fetchdf()
        except Exception as e:
            fixed_query = validate_and_fix_query(sql_query)
            result = con.execute(fixed_query).fetchdf()

        if result.empty:
            return {
                "messages": [IntermediateStep.from_text(json.dumps({
                    "result": "Query executed successfully but returned no results",
                    "query_executed": sql_query
                }))]
            }

        for col in result.select_dtypes(include=['float64', 'int64']).columns:
            result[col] = result[col].fillna(0)

        numeric_cols = result.select_dtypes(include=['float64', 'int64']).columns
        formatted_result = result.copy()
        for col in numeric_cols:
            if any(keyword in col.lower() for keyword in ['amount', 'cost', 'value', 'spent', 'outlay']):
                # Format as currency with commas for large numbers
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

        result_message = {
            "query_result": result_records,
            "messages": [IntermediateStep.from_text(json.dumps(result_dict))]
        }

        return result_message

    except Exception as e:
        error_msg = f"Query execution error: {str(e)}"
        return {
            "messages": [ErrorMessage.from_text(error_msg)]
        }

    finally:
        if con:
            con.close()
def route_query_replan(state: State) -> str:
    """
    Enhanced routing logic with better error handling
    """
    last_message = state['messages'][-1]
    retry_count = state.get('retry_count', 0)

    if isinstance(last_message, ErrorMessage) and retry_count < 3:
        state['retry_count'] = retry_count + 1
        return "replan"

    return "generate_result"
