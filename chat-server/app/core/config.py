from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Gopie Chat Server"
    API_V1_STR: str = "/api/v1"
    MODE: str = "development"

    MAX_TOOL_CALL_LIMIT: int = 10
    MAX_VALIDATION_RETRY_COUNT: int = 2
    MAX_SEMANTIC_SEARCH_RETRY: int = 1
    MAX_VIZ_TOOL_CALLS: int = 12

    CORS_ORIGINS: list[str] = ["*"]
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]

    LLM_GATEWAY_PROVIDER: str = ""
    EMBEDDING_GATEWAY_PROVIDER: str = ""

    PORTKEY_API_KEY: str = Field(default="", alias="PORTKEY_API_KEY")
    PORTKEY_URL: str = Field(default="", alias="PORTKEY_URL")
    PORTKEY_PROVIDER_API_KEY: str = Field(default="", alias="PORTKEY_PROVIDER_API_KEY")
    PORTKEY_PROVIDER_NAME: str = Field(default="", alias="PORTKEY_PROVIDER_NAME")
    PORTKEY_CONFIG_ID: str = Field(default="", alias="PORTKEY_CONFIG_ID")
    PORTKEY_EMBEDDING_PROVIDER_API_KEY: str = Field(
        default="", alias="PORTKEY_EMBEDDING_PROVIDER_API_KEY"
    )
    PORTKEY_EMBEDDING_PROVIDER_NAME: str = Field(
        default="", alias="PORTKEY_EMBEDDING_PROVIDER_NAME"
    )

    LITELLM_BASE_URL: str = Field(default="", alias="LITELLM_BASE_URL")
    LITELLM_MASTER_KEY: str = Field(default="", alias="LITELLM_MASTER_KEY")
    LITELLM_KEY_HEADER_NAME: str = Field(default="", alias="LITELLM_KEY_HEADER_NAME")
    LITELLM_VIRTUAL_KEY: str = Field(default="", alias="LITELLM_VIRTUAL_KEY")

    CLOUDFLARE_GATEWAY_URL: str = Field(default="", alias="CLOUDFLARE_GATEWAY_URL")
    CLOUDFLARE_API_TOKEN: str = Field(default="", alias="CLOUDFLARE_API_TOKEN")
    CLOUDFLARE_ACCOUNT_ID: str = Field(default="", alias="CLOUDFLARE_ACCOUNT_ID")
    CLOUDFLARE_GATEWAY_ID: str = Field(default="", alias="CLOUDFLARE_GATEWAY_ID")
    CLOUDFLARE_PROVIDER: str = Field(default="", alias="CLOUDFLARE_PROVIDER")
    CLOUDFLARE_PROVIDER_API_KEY: str = Field(default="", alias="CLOUDFLARE_PROVIDER_API_KEY")

    OPENROUTER_API_KEY: str = Field(default="", alias="OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL: str = Field(
        default="https://api.openrouter.ai", alias="OPENROUTER_BASE_URL"
    )

    LANGSMITH_PROMPT: bool = False
    LANGSMITH_API_KEY: str = Field(default="", alias="LANGSMITH_API_KEY")

    QDRANT_HOST: str = "host.docker.local"
    QDRANT_COLLECTION: str = "dataset_collection"
    QDRANT_DUCKDB_COLLECTION: str = "duckdb_docs_collection"
    QDRANT_PORT: int = 6333
    QDRANT_TOP_K: int = 5
    QDRANT_DUCKDB_TOP_K: int = 5

    GOPIE_API_ENDPOINT: str = ""

    ADVANCED_MODEL: str = ""
    BALANCED_MODEL: str = ""
    FAST_MODEL: str = ""
    FALLBACK_MODEL: str = ""  # only used by openrouter

    DETERMINISTIC_TEMPERATURE: float = 0.0
    LOW_VARIATION_TEMPERATURE: float = 0.3
    BALANCED_TEMPERATURE: float = 0.5
    CREATIVE_TEMPERATURE: float = 0.7

    DEFAULT_LLM_MODEL: str = ""
    DEFAULT_EMBEDDING_MODEL: str = ""
    DEFAULT_EMBEDDING_SIZE: int = 3072
    EMBEDDINGS_MAX_TOKEN: int | None = None
    DEFAULT_SPARSE_MODEL: str = "prithivida/Splade_PP_en_v1"

    E2B_API_KEY: str = ""
    E2B_TIMEOUT: int = 120

    INTERNAL_S3_HOST: str = ""
    EXTERNAL_S3_HOST: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = ""

    CUSTOM_EMBEDDING_BASE_URL: str = ""
    CUSTOM_EMBEDDING_API_KEY: str = ""

    CUSTOM_LLM_BASE_URL: str = ""
    CUSTOM_LLM_API_KEY: str = ""
    CUSTOM_PROVIDER_NAME: str = "other"

    # Provider-specific API keys (without CHAT_ prefix)
    OPENAI_API_KEY: str = Field(default="", alias="OPENAI_API_KEY")
    GROQ_API_KEY: str = Field(default="", alias="GROQ_API_KEY")
    TOGETHER_API_KEY: str = Field(default="", alias="TOGETHER_API_KEY")
    PERPLEXITY_API_KEY: str = Field(default="", alias="PERPLEXITY_API_KEY")
    FIREWORKS_API_KEY: str = Field(default="", alias="FIREWORKS_API_KEY")
    ANTHROPIC_API_KEY: str = Field(default="", alias="ANTHROPIC_API_KEY")
    DEEPINFRA_API_TOKEN: str = Field(default="", alias="DEEPINFRA_API_TOKEN")
    HF_TOKEN: str = Field(default="", alias="HF_TOKEN")

    CHAT_HISTORY_MAX_MESSAGES: int = 20
    CHAT_HISTORY_MAX_TOKENS: int = 10000

    ROW_TRUNCATION_LIMIT: int = 250
    DATASET_TOKEN_TRUNCATION_LIMIT: int = 100000
    COLUMN_TRUNCATION_LIMIT: int = 200
    DISPLAY_ROWS_AFTER_TRUNCATION_LIMIT: int = 20

    # Dataset Sampling Constants
    TARGET_ROWS: int = 150000
    SAMPLING_THRESHOLD: int = 150000

    # OLAP Backend Configuration
    OLAP_DB_TYPE: str = "duckdb"  # duckdb, motherduck, clickhouse, etc.

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", case_sensitive=True, env_prefix="CHAT_"
    )


settings = Settings()
