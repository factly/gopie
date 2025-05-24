from enum import Enum


class ModelCategory(str, Enum):
    ADVANCED = "advanced"
    BALANCED = "balanced"
    FAST = "fast"


class ModelVendor(str, Enum):
    OPENAI = "openai"
    GOOGLE = "google"


DEFAULT_VENDOR = ModelVendor.OPENAI
DEFAULT_CATEGORY = ModelCategory.ADVANCED
