from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Gopie Chat Server"
    API_V1_STR: str = "/api/v1"
    MODE: str = "development"

    LOG_DIR: str = "./server/logs"
    MAX_RETRY_COUNT: int = 3

    CORS_ORIGINS: list[str] = ["*"]
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]

    GATEWAY_PROVIDER: str = ""

    PORTKEY_API_KEY: str = ""
    GEMINI_VIRTUAL_KEY: str = ""
    OPENAI_VIRTUAL_KEY: str = ""
    PORTKEY_SELF_HOSTED_URL: str = ""

    LITELLM_BASE_URL: str = ""
    LITELLM_MASTER_KEY: str = ""

    CLOUDFLARE_GATEWAY_URL: str = ""
    CLOUDFLARE_API_TOKEN: str = ""
    CLOUDFLARE_ACCOUNT_ID: str = ""
    CLOUDFLARE_GATEWAY_ID: str = ""

    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    GOOGLE_PROJECT_ID: str = ""
    GOOGLE_LOCATION: str = ""
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    LANGSMITH_PROMPT: bool = False

    QDRANT_HOST: str = "host.docker.internal"
    QDRANT_COLLECTION: str = "dataset_collection"
    QDRANT_PORT: int = 6333
    QDRANT_TOP_K: int = 5

    GOPIE_API_ENDPOINT: str = ""

    MODEL_ANALYZE_QUERY: str = ""
    MODEL_ROUTE_QUERY_REPLAN: str = ""
    MODEL_GENERATE_SUBQUERIES: str = ""
    MODEL_IDENTIFY_DATASETS: str = ""
    MODEL_PLAN_QUERY: str = ""
    MODEL_GENERATE_RESULT: str = ""
    MODEL_STREAM_UPDATES: str = ""
    MODEL_CHECK_FURTHER_EXECUTION_REQUIREMENT: str = ""

    DEFAULT_OPENAI_MODEL: str = ""
    DEFAULT_EMBEDDING_MODEL: str = ""
    DEFAULT_GEMINI_MODEL: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = True


settings = Settings()
