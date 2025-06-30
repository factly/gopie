"""Tests for model registry functionality."""

from unittest.mock import Mock, patch

import pytest

from app.models.provider import ModelVendor
from app.tool_utils.tools import ToolNames
from app.utils.model_registry.model_provider import (
    ModelConfig,
    ModelProvider,
    get_chat_history,
    get_custom_model,
    get_gateway_provider,
    get_model_provider,
)
from app.utils.model_registry.model_selection import get_node_model


class TestModelConfig:
    """Test cases for ModelConfig class."""

    def test_model_config_default_initialization(self):
        """Test default ModelConfig initialization."""
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.DEFAULT_VENDOR = "openai"
            mock_settings.DEFAULT_OPENAI_MODEL = "gpt-4"
            mock_settings.DEFAULT_GEMINI_MODEL = "gemini-pro"

            config = ModelConfig()

            assert config.model_provider == ModelVendor.OPENAI
            assert config.openai_model == "gpt-4"
            assert config.gemini_model == "gemini-pro"

    def test_model_config_with_openai_model_id(self):
        """Test ModelConfig with OpenAI model ID."""
        with (
            patch(
                "app.utils.model_registry.model_provider.settings"
            ) as mock_settings,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gpt-3.5-turbo": Mock(provider=ModelVendor.OPENAI)},
            ),
        ):

            mock_settings.DEFAULT_VENDOR = "openai"

            config = ModelConfig(model_id="gpt-3.5-turbo")

            assert config.model_provider == ModelVendor.OPENAI
            assert config.openai_model == "gpt-3.5-turbo"

    def test_model_config_with_google_model_id(self):
        """Test ModelConfig with Google model ID."""
        with (
            patch(
                "app.utils.model_registry.model_provider.settings"
            ) as mock_settings,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gemini-1.5-pro": Mock(provider=ModelVendor.GOOGLE)},
            ),
        ):

            mock_settings.DEFAULT_VENDOR = "openai"

            config = ModelConfig(model_id="gemini-1.5-pro")

            assert config.model_provider == ModelVendor.GOOGLE
            assert config.gemini_model == "gemini-1.5-pro"

    def test_model_config_with_unknown_model_id(self):
        """Test ModelConfig with unknown model ID."""
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.DEFAULT_VENDOR = "openai"
            mock_settings.DEFAULT_OPENAI_MODEL = "gpt-4"

            config = ModelConfig(model_id="unknown-model")

            # Should use default configuration
            assert config.model_provider == ModelVendor.OPENAI
            assert config.openai_model == "gpt-4"


class TestGatewayProvider:
    """Test cases for gateway provider selection."""

    def test_get_gateway_provider_portkey_hosted(self, sample_metadata):
        """Test getting Portkey hosted gateway provider."""
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.GATEWAY_PROVIDER = "portkey_hosted"

            provider = get_gateway_provider(sample_metadata)

            from app.utils.providers.portkey import PortkeyGatewayProvider

            assert isinstance(provider, PortkeyGatewayProvider)

    def test_get_gateway_provider_portkey_self_hosted(self, sample_metadata):
        """Test getting Portkey self-hosted gateway provider."""
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.GATEWAY_PROVIDER = "portkey_self_hosted"

            provider = get_gateway_provider(sample_metadata)

            from app.utils.providers.portkey_self_hosted import (
                PortkeySelfHostedGatewayProvider,
            )

            assert isinstance(provider, PortkeySelfHostedGatewayProvider)

    def test_get_gateway_provider_litellm(self, sample_metadata):
        """Test getting LiteLLM gateway provider."""
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.GATEWAY_PROVIDER = "litellm"

            provider = get_gateway_provider(sample_metadata)

            from app.utils.providers.litellm import LiteLLMGatewayProvider

            assert isinstance(provider, LiteLLMGatewayProvider)

    def test_get_gateway_provider_cloudflare(self, sample_metadata):
        """Test getting Cloudflare gateway provider."""
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.GATEWAY_PROVIDER = "cloudflare"

            provider = get_gateway_provider(sample_metadata)

            from app.utils.providers.cloudflare import (
                CloudflareGatewayProvider,
            )

            assert isinstance(provider, CloudflareGatewayProvider)

    def test_get_gateway_provider_openrouter(self, sample_metadata):
        """Test getting OpenRouter gateway provider."""
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.GATEWAY_PROVIDER = "openrouter"

            provider = get_gateway_provider(sample_metadata)

            from app.utils.providers.openrouter import (
                OpenrouterGatewayProvider,
            )

            assert isinstance(provider, OpenrouterGatewayProvider)


class TestModelProvider:
    """Test cases for ModelProvider class."""

    @pytest.fixture
    def mock_gateway_provider(self):
        """Mock gateway provider."""
        return Mock(
            get_openai_model=Mock(return_value=Mock()),
            get_gemini_model=Mock(return_value=Mock()),
            get_embeddings_model=Mock(return_value=Mock()),
        )

    def test_model_provider_initialization(self, sample_metadata):
        """Test ModelProvider initialization."""
        with patch(
            "app.utils.model_registry.model_provider.get_gateway_provider"
        ) as mock_get_provider:
            mock_provider = Mock()
            mock_get_provider.return_value = mock_provider

            model_provider = ModelProvider(sample_metadata)

            assert model_provider.metadata == sample_metadata
            assert model_provider.gateway_provider == mock_provider

    def test_create_llm_openai_model(
        self, sample_metadata, mock_gateway_provider
    ):
        """Test creating OpenAI LLM."""
        with (
            patch(
                "app.utils.model_registry.model_provider.get_gateway_provider"
            ) as mock_get_provider,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gpt-4": Mock(provider=ModelVendor.OPENAI)},
            ),
        ):

            mock_get_provider.return_value = mock_gateway_provider

            model_provider = ModelProvider(sample_metadata)
            result = model_provider._create_llm("gpt-4")

            mock_gateway_provider.get_openai_model.assert_called_once_with(
                "gpt-4"
            )
            assert result is not None

    def test_create_llm_google_model(
        self, sample_metadata, mock_gateway_provider
    ):
        """Test creating Google LLM."""
        with (
            patch(
                "app.utils.model_registry.model_provider.get_gateway_provider"
            ) as mock_get_provider,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gemini-pro": Mock(provider=ModelVendor.GOOGLE)},
            ),
        ):

            mock_get_provider.return_value = mock_gateway_provider

            model_provider = ModelProvider(sample_metadata)
            result = model_provider._create_llm("gemini-pro")

            mock_gateway_provider.get_gemini_model.assert_called_once_with(
                "gemini-pro"
            )
            assert result is not None

    def test_create_llm_with_tools(
        self, sample_metadata, mock_gateway_provider
    ):
        """Test creating LLM with tools."""
        mock_tools = {"test_tool": (Mock(), {})}

        with (
            patch(
                "app.utils.model_registry.model_provider.get_gateway_provider"
            ) as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_tools"
            ) as mock_get_tools,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gpt-4": Mock(provider=ModelVendor.OPENAI)},
            ),
        ):

            mock_get_provider.return_value = mock_gateway_provider
            mock_get_tools.return_value = mock_tools
            mock_llm = Mock()
            mock_llm.bind_tools.return_value = Mock()
            mock_gateway_provider.get_openai_model.return_value = mock_llm

            model_provider = ModelProvider(sample_metadata)
            result = model_provider._create_llm_with_tools(
                "gpt-4", [ToolNames.EXECUTE_SQL_QUERY]
            )

            mock_llm.bind_tools.assert_called_once()
            assert result is not None

    def test_create_embeddings_model(
        self, sample_metadata, mock_gateway_provider
    ):
        """Test creating embeddings model."""
        with (
            patch(
                "app.utils.model_registry.model_provider.get_gateway_provider"
            ) as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.settings"
            ) as mock_settings,
        ):

            mock_get_provider.return_value = mock_gateway_provider
            mock_settings.DEFAULT_EMBEDDING_MODEL = "text-embedding-ada-002"

            model_provider = ModelProvider(sample_metadata)
            result = model_provider._create_embeddings_model()

            mock_gateway_provider.get_embeddings_model.assert_called_once_with(
                "text-embedding-ada-002"
            )
            assert result is not None

    def test_get_llm_for_node_without_tools(
        self, sample_metadata, mock_gateway_provider
    ):
        """Test getting LLM for node without tools."""
        with (
            patch(
                "app.utils.model_registry.model_provider.get_gateway_provider"
            ) as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_node_model"
            ) as mock_get_node_model,
        ):

            mock_get_provider.return_value = mock_gateway_provider
            mock_get_node_model.return_value = "gpt-4"

            model_provider = ModelProvider(sample_metadata)
            result = model_provider.get_llm_for_node("test_node")

            mock_get_node_model.assert_called_once_with("test_node")
            assert result is not None

    def test_get_llm_for_node_with_tools(
        self, sample_metadata, mock_gateway_provider
    ):
        """Test getting LLM for node with tools."""
        with (
            patch(
                "app.utils.model_registry.model_provider.get_gateway_provider"
            ) as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_node_model"
            ) as mock_get_node_model,
            patch(
                "app.utils.model_registry.model_provider.get_tools"
            ) as mock_get_tools,
        ):

            mock_get_provider.return_value = mock_gateway_provider
            mock_get_node_model.return_value = "gpt-4"
            mock_get_tools.return_value = {"tool": (Mock(), {})}
            mock_llm = Mock()
            mock_llm.bind_tools.return_value = Mock()
            mock_gateway_provider.get_openai_model.return_value = mock_llm

            model_provider = ModelProvider(sample_metadata)
            result = model_provider.get_llm_for_node(
                "test_node", [ToolNames.EXECUTE_SQL_QUERY]
            )

            mock_llm.bind_tools.assert_called_once()
            assert result is not None


class TestModelProviderUtilities:
    """Test cases for model provider utility functions."""

    def test_get_model_provider(self):
        """Test get_model_provider function."""
        # Use proper type annotation to avoid linter warnings
        config = {"configurable": {"metadata": {"user": "test_user"}}}

        with patch(
            "app.utils.model_registry.model_provider.ModelProvider"
        ) as mock_provider_class:
            mock_provider_instance = Mock()
            mock_provider_class.return_value = mock_provider_instance

            result = get_model_provider(config)  # type: ignore

            mock_provider_class.assert_called_once_with(
                metadata={"user": "test_user"}
            )
            assert result == mock_provider_instance

    def test_get_custom_model(self):
        """Test get_custom_model function."""
        with patch(
            "app.utils.model_registry.model_provider.ModelProvider"
        ) as mock_provider_class:
            mock_provider = Mock()
            mock_llm = Mock()
            mock_provider.get_llm.return_value = mock_llm
            mock_provider_class.return_value = mock_provider

            result = get_custom_model("gpt-4")

            mock_provider_class.assert_called_once_with(metadata={})
            mock_provider.get_llm.assert_called_once_with(model_id="gpt-4")
            assert result == mock_llm

    def test_get_chat_history(self):
        """Test get_chat_history function."""
        config = {"configurable": {"chat_history": ["message1", "message2"]}}

        result = get_chat_history(config)  # type: ignore

        assert result == ["message1", "message2"]

    def test_get_chat_history_default(self):
        """Test get_chat_history with default value."""
        config = {"configurable": {}}

        result = get_chat_history(config)  # type: ignore

        assert result == []


class TestModelSelection:
    """Test cases for model selection functionality."""

    def test_get_node_model(self):
        """Test get_node_model function."""
        with patch(
            "app.utils.model_registry.model_selection.settings"
        ) as mock_settings:
            mock_settings.DEFAULT_OPENAI_MODEL = "gpt-4"
            mock_settings.BALANCED_MODEL = ""  # Empty to fallback to default
            mock_settings.FAST_MODEL = ""
            mock_settings.ADVANCED_MODEL = ""

            # Test that it returns the default model for any node
            result = get_node_model("test_node")

            assert result == "gpt-4"
