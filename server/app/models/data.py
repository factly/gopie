from pydantic import BaseModel


class DatasetDetails(BaseModel):
    id: str
    name: str
    alias: str
    description: str
    file_path: str
    format: str
    row_count: int
    size: int
    columns: list
    created_at: str
    updated_at: str
    created_by: str
    updated_by: str
