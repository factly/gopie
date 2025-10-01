from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.log import custom_logger as logger

from .base import BaseLLMProvider


class CustomLLMProvider(BaseLLMProvider):
    # Combined mapping of provider names to their base URLs and API key settings
    PROVIDER_CONFIG = {
        "openai": {"base_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
        "groq": {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
        "togetherai": {
            "base_url": "https://api.together.xyz/v1",
            "api_key_env": "TOGETHER_API_KEY",
        },
        "perplexity": {
            "base_url": "https://api.perplexity.ai",
            "api_key_env": "PERPLEXITY_API_KEY",
        },
        "fireworks": {
            "base_url": "https://api.fireworks.ai/inference/v1",
            "api_key_env": "FIREWORKS_API_KEY",
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com/v1/",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
        "deepinfra": {
            "base_url": "https://api.deepinfra.com/v1/openai",
            "api_key_env": "DEEPINFRA_API_TOKEN",
        },
        "huggingface": {"base_url": "https://router.huggingface.co/v1", "api_key_env": "HF_TOKEN"},
        "other": {"base_url": settings.CUSTOM_LLM_BASE_URL, "api_key_env": "CUSTOM_LLM_API_KEY"},
    }

    def __init__(self, metadata: dict[str, str]):
        self.metadata = metadata

    def get_llm_model(
        self,
        model_name: str,
    ):
        # Get provider configuration (base URL and API key)
        base_url, api_key = self._get_provider_config()
        kwargs = {
            "api_key": api_key,
            "base_url": base_url,
            "model": model_name,
            "metadata": {
                **self.metadata,
            },
        }

        llm = ChatOpenAI(**kwargs)

        return llm

    def _get_provider_config(self) -> tuple[str, str]:
        """
        Get the appropriate base URL and API key based on the CUSTOM_LLM_GATEWAY_PROVIDER setting.
        Falls back to CUSTOM_LLM_BASE_URL and CUSTOM_LLM_API_KEY if provider is not recognized or not set.

        Returns:
            tuple[str, str]: (base_url, api_key)

        Raises:
            ValueError: If provider is specified but API key is not set
        """
        provider = settings.CUSTOM_PROVIDER_NAME.lower().strip()
        config = self.PROVIDER_CONFIG.get(provider, self.PROVIDER_CONFIG["other"])
        base_url = config["base_url"]
        api_key_env = config["api_key_env"]

        provider_api_key = getattr(settings, api_key_env, "")

        if not provider_api_key:
            raise ValueError(
                f"Provider '{provider}' is configured but the required API key '{api_key_env}' is not set. "
                f"Please set the {api_key_env} environment variable."
            )
        # Log which provider and base URL are being used
        logger.info(f"Using provider '{provider}' with base URL: {base_url}")
        return base_url, provider_api_key
