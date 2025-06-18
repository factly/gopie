from enum import Enum


class ModelCategory(str, Enum):
    ADVANCED = "advanced"
    BALANCED = "balanced"
    FAST = "fast"


class ModelVendor(str, Enum):
    OPENAI = "openai"
    GOOGLE = "google"


class GatewayProvider(str, Enum):
    PORTKEY_HOSTED = "portkey_hosted"
    PORTKEY_SELF_HOSTED = "portkey_self_hosted"
    LITELLM = "litellm"
    CLOUDFLARE = "cloudflare"
    OPENROUTER = "openrouter"
