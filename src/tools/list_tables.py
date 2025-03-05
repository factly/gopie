from langchain_core.tools import tool
import os

@tool
def list_tables() -> list[str]:
  """List all tables in a database"""
  data_dir = "./data"
  tables = []

  for file in os.listdir(data_dir):
    if file.endswith('.csv'):
      tables.append(file)

  return tables

__tool__ = list_tables