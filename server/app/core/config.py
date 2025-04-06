import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Dataful Agent"
    API_V1_STR: str = "/api/v1"
    MODE: str = "development"


    LOG_DIR: str = "./log"
    MAX_RETRY_COUNT: int = 3

    CORS_ORIGINS: List[str] = ["*"]
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDINGS_MODEL: str = "text-embedding-3-large"

    PORTKEY_API_KEY: str = os.getenv("PORTKEY_API_KEY", "")
    VIRTUAL_KEY: str = os.getenv("VIRTUAL_KEY", "")

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_TOP_K: int = 5

    MONGODB_PASSWORD: str = os.getenv("MONGODB_PASSWORD", "")
    MONGODB_USERNAME: str = os.getenv("MONGODB_USERNAME", "root")
    MONGODB_CONNECTION_STRING: str = f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@localhost:27017"
    HUNTING_API_URL: str = "http://localhost:8002/api/v1/prefetch"
    GOPIE_API_ENDPOINT: str = "http://localhost:8004"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()