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
    "o4-mini": ModelInfo(
        id="o4-mini",
        name="o4-mini",
        provider="OpenAI",
        description="Faster, more affordable reasoning model",
        is_default=False,
    ),
    "o3-mini": ModelInfo(
        id="o3-mini",
        name="o3-mini",
        provider="OpenAI",
        description="A small model alternative to o3",
        is_default=False,
    ),
    "gemini-2.5-flash-preview-04-17": ModelInfo(
        id="gemini-2.5-flash-preview-04-17",
        name="Gemini 2.5 Flash Preview 04-17",
        provider="Google",
        description="Adaptive thinking, cost efficiency",
        is_default=False,
    ),
    "gemini-2.5-pro-preview-05-06": ModelInfo(
        id="gemini-2.5-pro-preview-05-06",
        name="Gemini 2.5 Pro Preview 05-06",
        provider="Google",
        description="Enhanced thinking and reasoning, multimodal "
        "understanding, advanced coding, and more",
        is_default=False,
    ),
    "gemini-2.0-flash": ModelInfo(
        id="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider="Google",
        description="Next generation features, speed.",
        is_default=False,
    ),
}
