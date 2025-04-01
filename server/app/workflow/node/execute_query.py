import json
import logging
import os
import re

import duckdb
import pandas as pd
from langchain_core.output_parsers import JsonOutputParser

from server.app.core.langchain_config import lc
from server.app.models.types import ErrorMessage, IntermediateStep
from server.app.workflow.graph.types import State
from server.app.utils.dataset_info import DATA_DIR

MAX_RETRY_COUNT = 3


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", os.path.splitext(name)[0]).lower()


async def execute_query(state: State) -> dict:
    """
    Execute the planned query

    Args:
        state: The current state object containing messages and query information

    Returns:
        Updated state with query results or error messages
    """
    con = None
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    try:
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        if not last_message or isinstance(last_message, ErrorMessage):
            raise ValueError("No valid query plan found in messages")

        content = (
            last_message.content
            if isinstance(last_message.content, str)
            else json.dumps(last_message.content)
        )

        parser = JsonOutputParser()
        query_plan = parser.parse(content)

        if not query_plan:
            raise ValueError("Failed to parse query plan from message")

        con = duckdb.connect(database=":memory:")

        dataset_names = query_plan.get("tables_used", [])
        if not dataset_names:
            sql_query = query_plan.get("sql_query", "")
            if "FROM" in sql_query.upper():
                matches = re.finditer(
                    r"FROM\s+([^\s,;()]+)|JOIN\s+([^\s,;()]+)", sql_query, re.IGNORECASE
                )
                dataset_names = []
                for match in matches:
                    table = match.group(1) or match.group(2)
                    if table:
                        table = table.strip("\"'")
                        table = table.split("WHERE")[0].strip()
                        dataset_names.append(table)

        if not dataset_names:
            raise ValueError("No datasets specified in query plan")

        if isinstance(dataset_names, str):
            dataset_names = [dataset_names]

        table_mappings = {}

        for dataset_name in dataset_names:
            dataset_name = dataset_name.replace(".csv", "")
            matching_files = [
                f
                for f in os.listdir(DATA_DIR)
                if f.endswith(".csv") and dataset_name.lower() in f.lower()
            ]

            if not matching_files:
                raise FileNotFoundError(f"Dataset not found: {dataset_name}")

            file_path = os.path.join(DATA_DIR, matching_files[0])
            table_name = normalize_name(matching_files[0])
            table_mappings[dataset_name] = table_name

            df = pd.read_csv(file_path)
            logging.info(f"Loading dataset: {matching_files[0]} as table: {table_name}")

            for col in df.columns:
                if df[col].dtype == "object":
                    df[f"{col.lower()}_lower"] = df[col].str.lower()

            original_cols = df.columns
            clean_cols = {
                col: col.lower().strip().replace(" ", "_") for col in original_cols
            }
            df.rename(columns=clean_cols, inplace=True)

            try:
                con.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                con.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM df')
            except Exception as e:
                raise ValueError(
                    f"Failed to create table {table_name} in DuckDB: {str(e)}"
                )

        sql_query = query_plan.get("sql_query") or query_plan.get("sample_query")
        if not sql_query:
            raise ValueError("No SQL query found in plan")

        for dataset_name, table_name in table_mappings.items():
            sql_query = sql_query.replace(dataset_name, f'"{table_name}"')

        result = None
        try:
            result = con.execute(sql_query).fetchdf()
        except Exception as original_error:
            try:
                result = con.execute(sql_query).fetchdf()
            except Exception as fixed_error:
                raise ValueError(
                    f"Query execution failed. Original error: {str(original_error)}. "
                    f"After fixing: {str(fixed_error)}"
                )

        if result.empty:
            no_results_data = {
                "result": "Query executed successfully but returned no results",
                "query_executed": sql_query,
            }

            query_result.subqueries[query_index].query_result = []

            return {
                "query_result": query_result,
                "messages": [
                    IntermediateStep.from_text(json.dumps(no_results_data, indent=2))
                ],
            }

        for col in result.select_dtypes(include=["float64", "int64"]).columns:
            result[col] = result[col].fillna(0)

        result_records = result.to_dict("records")

        result_dict = {
            "result": "Query executed successfully",
            "query_executed": sql_query,
            "data": result_records,
        }

        query_result.subqueries[query_index].sql_query_used = sql_query
        query_result.subqueries[query_index].query_result = result_records

        return {
            "query_result": query_result,
            "messages": [IntermediateStep.from_text(json.dumps(result_dict, indent=2))],
        }

    except Exception as e:
        error_msg = f"Query execution error: {str(e)}"
        query_result.add_error_message(error_msg, "Query execution")

        return {
            "query_result": query_result,
            "messages": [
                ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))
            ],
            "retry_count": state.get("retry_count", 0) + 1,
        }

    finally:
        if con:
            con.close()


async def route_query_replan(state: State) -> str:
    """
    Determine whether to replan the query or generate results based on execution status

    Args:
        state: The current state containing messages and retry information

    Returns:
        Routing decision: "replan" or "generate_result"
    """
    last_message = state["messages"][-1]
    retry_count = state.get("retry_count", 0)

    if isinstance(last_message, ErrorMessage) and retry_count < MAX_RETRY_COUNT:
        response = await lc.llm.ainvoke(
            f"""
                I got an error when executing the query: "{last_message.content}"

                Can you please tell whether this error can be solved by replanning the query? or it's need to reidentify the datasets?

                If it's need to reidentify the datasets, please return "reidentify_datasets"
                If it's need to replan the query, please return "replan"
                If it's no problem, please return "response_router"
            """
        )

        response_text = str(response.content).lower()

        if "reidentify_datasets" in response_text:
            return "reidentify_datasets"
        elif "replan" in response_text:
            return "replan"
        else:
            return "response_router"

    return "response_router"
