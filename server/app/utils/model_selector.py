from app.models.router import ModelInfo

AVAILABLE_MODELS: dict[str, ModelInfo] = {
    "gpt-4o": ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        description="OpenAI's GPT-4o model - fast, powerful reasoning "
        "with tool use capabilities",
        is_default=True,
    ),
    "gpt-4o-mini": ModelInfo(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider="OpenAI",
        description="OpenAI's smaller GPT-4o model - efficient and "
        "cost-effective",
        is_default=False,
    ),
    "gemini-2.0-flash": ModelInfo(
        id="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider="Google",
        description="Google's Gemini 2.0 Flash model - fast, efficient "
        "reasoning",
        is_default=False,
    ),
    "gemini-2.5-pro-preview-05-06": ModelInfo(
        id="gemini-2.5-pro-preview-05-06",
        name="Gemini 2.5 Pro Preview 05-06",
        provider="Google",
        description="Google's Gemini 2.5 Pro model - powerful reasoning "
        "capabilities",
        is_default=False,
    ),
    "gemini-2.0-pro": ModelInfo(
        id="gemini-2.0-pro",
        name="Gemini 2.0 Pro",
        provider="Google",
        description="Google's Gemini 2.0 Pro model - powerful reasoning "
        "capabilities",
        is_default=False,
    ),
}
