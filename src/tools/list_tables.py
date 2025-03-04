from langchain_core.tools import tool
import os

def get_data_directory() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data')

@tool
def list_tables() -> str:
  """List all tables in a database"""
  data_dir = get_data_directory()
  tables = os.listdir(data_dir)
  return "\n".join(tables)