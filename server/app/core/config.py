from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Dataful Agent"
    API_V1_STR: str = "/api/v1"
    MODE: str = "development"

    LOG_DIR: str = "./server/logs"
    MAX_RETRY_COUNT: int = 3

    CORS_ORIGINS: list[str] = ["*"]
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]

    PORTKEY_API_KEY: str = ""

    GEMINI_MODEL: str = "gemini-2.5-pro-preview-03-25"
    GEMINI_VIRTUAL_KEY: str = ""

    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDINGS_MODEL: str = "text-embedding-3-large"
    OPENAI_VIRTUAL_KEY: str = ""

    QDRANT_HOST: str = "host.docker.internal"
    QDRANT_COLLECTION: str = "dataset_collection"
    QDRANT_PORT: int = 6333
    QDRANT_TOP_K: int = 5

    HUNTING_API_PREFETCH_ENDPOINT: str = (
        "http://host.docker.internal:8003/api/v1/prefetch"
    )
    HUNTING_API_DESCRIPTION_ENDPOINT: str = (
        "http://host.docker.internal:8003/api/v1/profile/description"
    )
    FLOWER_API_ENDPOINT: str = ""
    GOPIE_API_ENDPOINT: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = True


settings = Settings()
