from unittest.mock import Mock, patch

import pytest

from app.models.provider import ModelCategory, ModelVendor
from app.tool_utils.tools import ToolNames
from app.utils.model_registry.model_provider import (
    ModelConfig,
    ModelProvider,
    get_chat_history,
    get_custom_model,
    get_llm_provider,
    get_model_provider,
)
from app.utils.model_registry.model_selection import get_node_model


class TestModelConfig:
    def test_model_config_default_initialization(self):
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
        with (
            patch(
                "app.utils.model_registry.model_provider.settings"
            ) as mock_settings,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gpt-3.5-turbo": Mock(provider=ModelVendor.OPENAI.value)},
            ),
        ):

            mock_settings.DEFAULT_VENDOR = "openai"

            config = ModelConfig(model_id="gpt-3.5-turbo")

            assert config.model_provider == ModelVendor.OPENAI
            assert config.openai_model == "gpt-3.5-turbo"

    def test_model_config_with_google_model_id(self):
        with (
            patch(
                "app.utils.model_registry.model_provider.settings"
            ) as mock_settings,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gemini-1.5-pro": Mock(provider=ModelVendor.GOOGLE.value)},
            ),
        ):

            mock_settings.DEFAULT_VENDOR = "openai"

            config = ModelConfig(model_id="gemini-1.5-pro")

            assert config.model_provider == ModelVendor.GOOGLE
            assert config.gemini_model == "gemini-1.5-pro"

    def test_model_config_with_unknown_model_id(self):
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.DEFAULT_VENDOR = "openai"
            mock_settings.DEFAULT_OPENAI_MODEL = "gpt-4"

            config = ModelConfig(model_id="unknown-model")

            assert config.model_provider == ModelVendor.OPENAI
            assert config.openai_model == "gpt-4"


class TestLLMProvider:
    def test_get_llm_provider_portkey_hosted(self, sample_metadata):
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.GATEWAY_PROVIDER = "portkey_hosted"

            provider = get_llm_provider(sample_metadata)

            from app.utils.llm_providers.portkey import PortkeyLLMProvider

            assert isinstance(provider, PortkeyLLMProvider)

    def test_get_llm_provider_portkey_self_hosted(self, sample_metadata):
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.GATEWAY_PROVIDER = "portkey_self_hosted"

            provider = get_llm_provider(sample_metadata)

            from app.utils.llm_providers.portkey_self_hosted import (
                PortkeySelfHostedLLMProvider,
            )

            assert isinstance(provider, PortkeySelfHostedLLMProvider)

    def test_get_llm_provider_litellm(self, sample_metadata):
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.GATEWAY_PROVIDER = "litellm"

            provider = get_llm_provider(sample_metadata)

            from app.utils.llm_providers.litellm import LiteLLMProvider

            assert isinstance(provider, LiteLLMProvider)

    def test_get_llm_provider_cloudflare(self, sample_metadata):
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.GATEWAY_PROVIDER = "cloudflare"

            provider = get_llm_provider(sample_metadata)

            from app.utils.llm_providers.cloudflare import (
                CloudflareLLMProvider,
            )

            assert isinstance(provider, CloudflareLLMProvider)

    def test_get_llm_provider_openrouter(self, sample_metadata):
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.GATEWAY_PROVIDER = "openrouter"

            provider = get_llm_provider(sample_metadata)

            from app.utils.llm_providers.openrouter import (
                OpenRouterLLMProvider,
            )

            assert isinstance(provider, OpenRouterLLMProvider)

    def test_get_llm_provider_custom(self, sample_metadata):
        with patch(
            "app.utils.model_registry.model_provider.settings"
        ) as mock_settings:
            mock_settings.GATEWAY_PROVIDER = "custom"

            provider = get_llm_provider(sample_metadata)

            from app.utils.llm_providers.custom import CustomLLMProvider

            assert isinstance(provider, CustomLLMProvider)


class TestModelProvider:
    @pytest.fixture
    def mock_llm_provider(self):
        return Mock(
            get_openai_model=Mock(return_value=Mock()),
            get_gemini_model=Mock(return_value=Mock()),
        )

    @pytest.fixture
    def mock_embedding_provider(self):
        return Mock(
            get_embeddings_model=Mock(return_value=Mock()),
        )

    def test_model_provider_initialization(self, sample_metadata):
        with (
            patch(
                "app.utils.model_registry.model_provider.get_llm_provider"
            ) as mock_get_llm_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
        ):
            mock_llm_provider = Mock()
            mock_embedding_provider = Mock()
            mock_get_llm_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = mock_embedding_provider

            model_provider = ModelProvider(sample_metadata)

            assert model_provider.metadata == sample_metadata
            assert model_provider.llm_provider == mock_llm_provider
            assert model_provider.embedding_provider == mock_embedding_provider

    def test_create_llm_openai_model(self, sample_metadata, mock_llm_provider):
        with (
            patch(
                "app.utils.model_registry.model_provider.get_llm_provider"
            ) as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gpt-4": Mock(provider=ModelVendor.OPENAI.value)},
            ),
        ):

            mock_get_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = Mock()

            model_provider = ModelProvider(sample_metadata)
            result = model_provider._create_llm("gpt-4")

            mock_llm_provider.get_openai_model.assert_called_once_with("gpt-4")
            assert result is not None

    def test_create_llm_google_model(self, sample_metadata, mock_llm_provider):
        with (
            patch(
                "app.utils.model_registry.model_provider.get_llm_provider"
            ) as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gemini-pro": Mock(provider=ModelVendor.GOOGLE.value)},
            ),
        ):

            mock_get_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = Mock()

            model_provider = ModelProvider(sample_metadata)
            result = model_provider._create_llm("gemini-pro")

            mock_llm_provider.get_gemini_model.assert_called_once_with(
                "gemini-pro"
            )
            assert result is not None

    def test_create_llm_with_tools(self, sample_metadata, mock_llm_provider):
        mock_tools = {"test_tool": (Mock(), {})}

        with (
            patch(
                "app.utils.model_registry.model_provider.get_llm_provider"
            ) as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
            patch(
                "app.utils.model_registry.model_provider.get_tools"
            ) as mock_get_tools,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gpt-4": Mock(provider=ModelVendor.OPENAI.value)},
            ),
        ):

            mock_get_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = Mock()
            mock_get_tools.return_value = mock_tools
            mock_llm = Mock()
            mock_llm.bind_tools.return_value = Mock()
            mock_llm_provider.get_openai_model.return_value = mock_llm

            model_provider = ModelProvider(sample_metadata)
            result = model_provider._create_llm_with_tools(
                "gpt-4", [ToolNames.EXECUTE_SQL_QUERY]
            )

            mock_llm.bind_tools.assert_called_once()
            assert result is not None

    def test_get_llm_for_node_without_tools(
        self, sample_metadata, mock_llm_provider
    ):
        with (
            patch(
                "app.utils.model_registry.model_provider.get_llm_provider"
            ) as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
            patch(
                "app.utils.model_registry.model_provider.get_node_model"
            ) as mock_get_node_model,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gpt-4": Mock(provider=ModelVendor.OPENAI.value)},
            ),
        ):

            mock_get_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = Mock()
            mock_get_node_model.return_value = "gpt-4"

            model_provider = ModelProvider(sample_metadata)
            result = model_provider.get_llm_for_node("test_node")

            mock_get_node_model.assert_called_once_with("test_node")
            assert result is not None

    def test_get_llm_for_node_with_tools(
        self, sample_metadata, mock_llm_provider
    ):
        with (
            patch(
                "app.utils.model_registry.model_provider.get_llm_provider"
            ) as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
            patch(
                "app.utils.model_registry.model_provider.get_node_model"
            ) as mock_get_node_model,
            patch(
                "app.utils.model_registry.model_provider.get_tools"
            ) as mock_get_tools,
            patch.dict(
                "app.utils.model_registry.model_provider.AVAILABLE_MODELS",
                {"gpt-4": Mock(provider=ModelVendor.OPENAI.value)},
            ),
        ):

            mock_get_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = Mock()
            mock_get_node_model.return_value = "gpt-4"
            mock_get_tools.return_value = {"tool": (Mock(), {})}
            mock_llm = Mock()
            mock_llm.bind_tools.return_value = Mock()
            mock_llm_provider.get_openai_model.return_value = mock_llm

            model_provider = ModelProvider(sample_metadata)
            result = model_provider.get_llm_for_node(
                "test_node", [ToolNames.EXECUTE_SQL_QUERY]
            )

            mock_llm.bind_tools.assert_called_once()
            assert result is not None

    def test_create_embeddings_model(
        self, sample_metadata, mock_embedding_provider
    ):
        with (
            patch(
                "app.utils.model_registry.model_provider.get_llm_provider"
            ) as mock_get_llm_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
            patch(
                "app.utils.model_registry.model_provider.settings"
            ) as mock_settings,
        ):
            mock_get_llm_provider.return_value = Mock()
            mock_get_embedding_provider.return_value = mock_embedding_provider
            mock_settings.DEFAULT_EMBEDDING_MODEL = "text-embedding-ada-002"

            model_provider = ModelProvider(sample_metadata)
            result = model_provider._create_embeddings_model()

            mock_embedding_provider.get_embeddings_model.assert_called_once_with(
                "text-embedding-ada-002"
            )
            assert result is not None


class TestModelProviderUtilities:
    def test_get_model_provider(self):
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
        config = {"configurable": {"chat_history": ["message1", "message2"]}}

        result = get_chat_history(config)  # type: ignore

        assert result == ["message1", "message2"]

    def test_get_chat_history_default(self):
        config = {"configurable": {}}

        result = get_chat_history(config)  # type: ignore

        assert result == []


class TestModelSelection:
    def test_get_node_model(self):
        with (
            patch(
                "app.utils.model_registry.model_selection.settings"
            ) as mock_settings,
            patch.dict(
                "app.utils.model_registry.model_selection.COMPLEXITY_TO_MODEL",
                {
                    ModelCategory.BALANCED: "",
                    ModelCategory.FAST: "",
                    ModelCategory.ADVANCED: "",
                },
            ),
            patch.dict(
                "app.utils.model_registry.model_selection.NODE_TO_COMPLEXITY",
                {"test_node": ModelCategory.BALANCED},
            ),
        ):
            mock_settings.DEFAULT_OPENAI_MODEL = "gpt-4"

            result = get_node_model("test_node")

            assert result == "gpt-4"
