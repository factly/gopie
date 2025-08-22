from enum import Enum

from app.core.config import settings


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
    DETERMINISTIC = settings.DETERMINISTIC_TEMPERATURE  # Analysis, validation, routing
    LOW_VARIATION = (
        settings.LOW_VARIATION_TEMPERATURE
    )  # SQL generation, structured output with slight variation
    BALANCED = settings.BALANCED_TEMPERATURE  # General processing, context analysis
    CREATIVE = settings.CREATIVE_TEMPERATURE  # Natural language generation, summarization
    NONE = None  # No temperature setting, used for deterministic outputs
