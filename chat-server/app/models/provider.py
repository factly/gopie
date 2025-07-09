from enum import Enum


class ModelCategory(str, Enum):
    ADVANCED = "advanced"
    BALANCED = "balanced"
    FAST = "fast"


class LLMProvider(str, Enum):
    PORTKEY = "portkey"
    LITELLM = "litellm"
    CLOUDFLARE = "cloudflare"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"


class EmbeddingProvider(str, Enum):
    PORTKEY = "portkey"
    LITELLM = "litellm"
    OPENAI = "openai"
    CUSTOM = "custom"
