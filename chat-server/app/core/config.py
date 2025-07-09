from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Gopie Chat Server"
    API_V1_STR: str = "/api/v1"
    MODE: str = "development"

    MAX_RETRY_COUNT: int = 3
    MAX_VALIDATION_RETRY_COUNT: int = 2

    CORS_ORIGINS: list[str] = ["*"]
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]

    LLM_GATEWAY_PROVIDER: str = ""
    EMBEDDING_GATEWAY_PROVIDER: str = ""

    PORTKEY_API_KEY: str = ""
    PORTKEY_URL: str = ""
    PORTKEY_PROVIDER_API_KEY: str = ""
    PORTKEY_PROVIDER_NAME: str = ""
    PORTKEY_CONFIG_ID: str = ""
    PORTKEY_EMBEDDING_PROVIDER_API_KEY: str = ""
    PORTKEY_EMBEDDING_PROVIDER_NAME: str = ""

    LITELLM_BASE_URL: str = ""
    LITELLM_MASTER_KEY: str = ""
    LITELLM_KEY_HEADER_NAME: str = ""
    LITELLM_VIRTUAL_KEY: str = ""

    CLOUDFLARE_GATEWAY_URL: str = ""
    CLOUDFLARE_API_TOKEN: str = ""
    CLOUDFLARE_ACCOUNT_ID: str = ""
    CLOUDFLARE_GATEWAY_ID: str = ""
    CLOUDFLARE_PROVIDER: str = ""
    CLOUDFLARE_PROVIDER_API_KEY: str = ""

    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    GOOGLE_PROJECT_ID: str = ""
    GOOGLE_LOCATION: str = ""
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = ""

    LANGSMITH_PROMPT: bool = False
    LANGSMITH_API_KEY: str = ""

    QDRANT_HOST: str = "host.docker.internal"
    QDRANT_COLLECTION: str = "dataset_collection"
    QDRANT_PORT: int = 6333
    QDRANT_TOP_K: int = 5

    GOPIE_API_ENDPOINT: str = ""

    ADVANCED_MODEL: str = ""
    BALANCED_MODEL: str = ""
    FAST_MODEL: str = ""

    DEFAULT_LLM_MODEL: str = ""
    DEFAULT_EMBEDDING_MODEL: str = ""

    E2B_API_KEY: str = ""
    E2B_TIMEOUT: int = 120

    S3_HOST: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = ""

    CUSTOM_EMBEDDING_BASE_URL: str = ""
    CUSTOM_EMBEDDING_API_KEY: str = ""
    CUSTOM_EMBEDDING_MODEL: str = ""

    CUSTOM_LLM_BASE_URL: str = ""
    CUSTOM_LLM_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", case_sensitive=True
    )


settings = Settings()
