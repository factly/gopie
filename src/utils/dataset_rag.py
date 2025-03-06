import os
import pandas as pd
from typing import Dict, List
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def get_dataset_schemas() -> Dict[str, List[str]]:
    """Get schemas for all CSV files in the data directory."""
    data_dir = "data"
    schemas = {}

    for file in os.listdir(data_dir):
        if file.endswith('.csv'):
            file_path = os.path.join(data_dir, file)
            df = pd.read_csv(file_path)
            schemas[file] = list(df.columns)

    return schemas

def main():
    schemas = get_dataset_schemas()

    for filename, columns in schemas.items():
        print(f"\nSchema for {filename}:")
        print("Columns:", columns)

        schema_text = f"Dataset {filename} contains columns: {', '.join(columns)}"

        try:
            embedding = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
            vector = embedding.embed_query(schema_text)
            vector[:5]

            print(f"Embedding shape: {len(vector)}")
            print("First few values:", vector[:5])
        except Exception as e:
            print(f"Error generating embedding: {e}")

if __name__ == "__main__":
    main()