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


class TemperatureCategory(Enum):
    DETERMINISTIC = 0.0  # Analysis, validation, routing
    LOW_VARIATION = 0.3  # SQL generation, structured output with slight variation
    BALANCED = 0.5  # General processing, context analysis
    CREATIVE = 0.7  # Natural language generation, summarization
