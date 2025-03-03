import json
from langchain_core.output_parsers import JsonOutputParser
import os
import re
import duckdb
import pandas as pd
from lib.graph.types import ErrorMessage, State, IntermediateStep
from typing import Dict, Any
from lib.config.langchain_config import lc

MAX_RETRY_COUNT = 3

def get_data_directory() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data')

def normalize_name(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', os.path.splitext(name)[0]).lower()

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

        parser = JsonOutputParser()
        query_plan = parser.parse(content)

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
                result = con.execute(sql_query).fetchdf()
            except Exception as fixed_error:
                raise ValueError(f"Query execution failed. Original error: {str(original_error)}. "
                                f"After fixing: {str(fixed_error)}")

        if result.empty:
            no_results_data = {
                "result": "Query executed successfully but returned no results",
                "query_executed": sql_query,
            }
            return {
                "messages": [ErrorMessage.from_text(json.dumps(no_results_data, indent=2))],
                "retry_count": state.get('retry_count', 0) + 1
            }

        for col in result.select_dtypes(include=['float64', 'int64']).columns:
            result[col] = result[col].fillna(0)

        result_records = result.to_dict('records')

        result_dict = {
            "result": "Query executed successfully",
            "query_executed": sql_query,
            "data": result_records,
        }

        return {
            "query_result": result_records,
            "messages": [IntermediateStep.from_text(json.dumps(result_dict, indent=2))]
        }

    except Exception as e:
        error_msg = f"Query execution error: {str(e)}"
        return {
            "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))],
            "retry_count": state.get('retry_count', 0) + 1
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
    retry_count = state.get('retry_count', 0)

    if isinstance(last_message, ErrorMessage) and retry_count < MAX_RETRY_COUNT:
        response = lc.llm.invoke(
            f"""
                I got an error when executing the query: "{last_message.content}"

                Can you please tell whether this error can be solved by replanning the query? or it's need to reidentify the datasets?

                If it's need to reidentify the datasets, please return "reidentify_datasets"
                If it's need to replan the query, please return "replan"
                If it's no problem, please return "generate_result"
            """
        )

        return JsonOutputParser().parse(str(response.content))

    return "generate_result"