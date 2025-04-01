import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Dataful Agent"
    API_V1_STR: str = "/api/v1"

    CORS_ORIGINS: List[str] = ["*"]
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    DATA_DIR: str = os.getenv("DATA_DIR", "./data")

    LOG_DIR: str = os.getenv("LOG_DIR", "./log")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_EMBEDDINGS_MODEL: str = os.getenv("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-large")

    PORTKEY_API_KEY: str = os.getenv("PORTKEY_API_KEY", "")
    VIRTUAL_KEY: str = os.getenv("VIRTUAL_KEY", "")
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()