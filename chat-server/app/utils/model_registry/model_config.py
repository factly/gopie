from app.models.provider import ModelVendor
from app.models.router import ModelInfo

AVAILABLE_MODELS: dict[str, ModelInfo] = {
    "gpt-4o": ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        provider=ModelVendor.OPENAI,
        description="OpenAI's GPT-4o model - powerful reasoning with tool use",
        is_default=True,
    ),
    "gpt-4o-mini": ModelInfo(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider=ModelVendor.OPENAI,
        description="OpenAI's smaller GPT-4o model - efficient and balanced",
        is_default=False,
    ),
    "o4-mini": ModelInfo(
        id="o4-mini",
        name="o4-mini",
        provider=ModelVendor.OPENAI,
        description="Faster, more affordable reasoning model",
        is_default=False,
    ),
    "gemini-2.5-pro-preview-05-06": ModelInfo(
        id="gemini-2.5-pro-preview-05-06",
        name="Gemini 2.5 Pro Preview 05-06",
        provider=ModelVendor.GOOGLE,
        description="Enhanced reasoning and multimodal understanding",
        is_default=False,
    ),
    "gemini-2.5-flash-preview-04-17": ModelInfo(
        id="gemini-2.5-flash-preview-04-17",
        name="Gemini 2.5 Flash Preview 04-17",
        provider=ModelVendor.GOOGLE,
        description="Adaptive thinking, cost efficiency",
        is_default=False,
    ),
    "gemini-2.0-flash": ModelInfo(
        id="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider=ModelVendor.GOOGLE,
        description="Next generation features, speed",
        is_default=False,
    ),
}
