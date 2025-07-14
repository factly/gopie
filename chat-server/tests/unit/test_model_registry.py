from unittest.mock import Mock, patch

import pytest

from app.tool_utils.tools import ToolNames
from app.utils.model_registry.model_provider import (
    ModelProvider,
    get_chat_history,
    get_custom_model,
    get_embedding_provider,
    get_llm_provider,
    get_model_provider,
)


class TestLLMProvider:
    def test_get_llm_provider_portkey(self, sample_metadata):
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.LLM_GATEWAY_PROVIDER = "portkey"

            provider = get_llm_provider(sample_metadata)

            from app.utils.providers.llm_providers.portkey import PortkeyLLMProvider

            assert isinstance(provider, PortkeyLLMProvider)

    def test_get_llm_provider_litellm(self, sample_metadata):
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.LLM_GATEWAY_PROVIDER = "litellm"

            provider = get_llm_provider(sample_metadata)

            from app.utils.providers.llm_providers.litellm import LiteLLMProvider

            assert isinstance(provider, LiteLLMProvider)

    def test_get_llm_provider_cloudflare(self, sample_metadata):
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.LLM_GATEWAY_PROVIDER = "cloudflare"

            provider = get_llm_provider(sample_metadata)

            from app.utils.providers.llm_providers.cloudflare import CloudflareLLMProvider

            assert isinstance(provider, CloudflareLLMProvider)

    def test_get_llm_provider_openrouter(self, sample_metadata):
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.LLM_GATEWAY_PROVIDER = "openrouter"

            provider = get_llm_provider(sample_metadata)

            from app.utils.providers.llm_providers.openrouter import OpenRouterLLMProvider

            assert isinstance(provider, OpenRouterLLMProvider)

    def test_get_llm_provider_custom(self, sample_metadata):
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.LLM_GATEWAY_PROVIDER = "custom"

            provider = get_llm_provider(sample_metadata)

            from app.utils.providers.llm_providers.custom import CustomLLMProvider

            assert isinstance(provider, CustomLLMProvider)


class TestEmbeddingProvider:
    def test_get_embedding_provider_portkey(self, sample_metadata):
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.EMBEDDING_GATEWAY_PROVIDER = "portkey"

            provider = get_embedding_provider(sample_metadata)

            from app.utils.providers.embedding_providers.portkey import PortkeyEmbeddingProvider

            assert isinstance(provider, PortkeyEmbeddingProvider)

    def test_get_embedding_provider_litellm(self, sample_metadata):
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.EMBEDDING_GATEWAY_PROVIDER = "litellm"

            provider = get_embedding_provider(sample_metadata)

            from app.utils.providers.embedding_providers.litellm import LiteLLMEmbeddingProvider

            assert isinstance(provider, LiteLLMEmbeddingProvider)

    def test_get_embedding_provider_openai(self, sample_metadata):
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.EMBEDDING_GATEWAY_PROVIDER = "openai"

            provider = get_embedding_provider(sample_metadata)

            from app.utils.providers.embedding_providers.openai import OpenAIEmbeddingProvider

            assert isinstance(provider, OpenAIEmbeddingProvider)

    def test_get_embedding_provider_custom(self, sample_metadata):
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.EMBEDDING_GATEWAY_PROVIDER = "custom"

            provider = get_embedding_provider(sample_metadata)

            from app.utils.providers.embedding_providers.custom import CustomEmbeddingProvider

            assert isinstance(provider, CustomEmbeddingProvider)


class TestModelProvider:
    @pytest.fixture
    def mock_llm_provider(self):
        return Mock(
            get_llm_model=Mock(return_value=Mock()),
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

    def test_create_llm_model(self, sample_metadata, mock_llm_provider):
        with (
            patch("app.utils.model_registry.model_provider.get_llm_provider") as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
        ):

            mock_get_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = Mock()

            model_provider = ModelProvider(sample_metadata)
            result = model_provider._create_llm("gpt-4")

            mock_llm_provider.get_llm_model.assert_called_once_with("gpt-4")
            assert result is not None

    def test_create_llm_with_tools(self, sample_metadata, mock_llm_provider):
        mock_tools = {"test_tool": (Mock(), {})}
        mock_llm = Mock()
        mock_llm.bind_tools.return_value = Mock()
        mock_llm_provider.get_llm_model.return_value = mock_llm

        with (
            patch("app.utils.model_registry.model_provider.get_llm_provider") as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
            patch("app.utils.model_registry.model_provider.get_tools") as mock_get_tools,
        ):

            mock_get_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = Mock()
            mock_get_tools.return_value = mock_tools

            model_provider = ModelProvider(sample_metadata)
            result = model_provider._create_llm_with_tools("gpt-4", [ToolNames.EXECUTE_SQL_QUERY])

            mock_llm_provider.get_llm_model.assert_called_once_with("gpt-4")
            mock_get_tools.assert_called_once_with([ToolNames.EXECUTE_SQL_QUERY])
            mock_llm.bind_tools.assert_called_once()
            assert result is not None

    def test_get_llm_for_node_without_tools(self, sample_metadata, mock_llm_provider):
        with (
            patch("app.utils.model_registry.model_provider.get_llm_provider") as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
            patch("app.utils.model_registry.model_provider.get_node_model") as mock_get_node_model,
        ):
            mock_get_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = Mock()
            mock_get_node_model.return_value = "gpt-4"

            model_provider = ModelProvider(sample_metadata)
            result = model_provider.get_llm_for_node("test_node")

            mock_get_node_model.assert_called_once_with("test_node")
            mock_llm_provider.get_llm_model.assert_called_once_with("gpt-4")
            assert result is not None

    def test_get_llm_for_node_with_tools(self, sample_metadata, mock_llm_provider):
        mock_tools = {"test_tool": (Mock(), {})}
        mock_llm = Mock()
        mock_llm.bind_tools.return_value = Mock()
        mock_llm_provider.get_llm_model.return_value = mock_llm

        with (
            patch("app.utils.model_registry.model_provider.get_llm_provider") as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
            patch("app.utils.model_registry.model_provider.get_node_model") as mock_get_node_model,
            patch("app.utils.model_registry.model_provider.get_tools") as mock_get_tools,
        ):
            mock_get_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = Mock()
            mock_get_node_model.return_value = "gpt-4"
            mock_get_tools.return_value = mock_tools

            model_provider = ModelProvider(sample_metadata)
            result = model_provider.get_llm_for_node("test_node", [ToolNames.EXECUTE_SQL_QUERY])

            # get_node_model is called twice - once in get_llm_for_node and once in get_llm_with_tools
            assert mock_get_node_model.call_count == 2
            mock_get_node_model.assert_any_call("test_node")
            mock_get_node_model.assert_any_call(
                "gpt-4"
            )  # This is the model_id passed to get_llm_with_tools
            mock_llm_provider.get_llm_model.assert_called_once_with("gpt-4")
            mock_get_tools.assert_called_once_with([ToolNames.EXECUTE_SQL_QUERY])
            mock_llm.bind_tools.assert_called_once()
            assert result is not None

    def test_create_embeddings_model(self, sample_metadata, mock_embedding_provider):
        with (
            patch(
                "app.utils.model_registry.model_provider.get_llm_provider"
            ) as mock_get_llm_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
            patch("app.utils.model_registry.model_provider.settings") as mock_settings,
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
        from langchain_core.runnables import RunnableConfig

        config = RunnableConfig(
            configurable={"metadata": {"user": "test_user", "trace_id": "test_trace"}}
        )

        with (
            patch(
                "app.utils.model_registry.model_provider.get_llm_provider"
            ) as mock_get_llm_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
        ):
            mock_get_llm_provider.return_value = Mock()
            mock_get_embedding_provider.return_value = Mock()

            result = get_model_provider(config)

            assert isinstance(result, ModelProvider)
            assert result.metadata == {"user": "test_user", "trace_id": "test_trace"}

    def test_get_custom_model(self):
        with (
            patch(
                "app.utils.model_registry.model_provider.get_llm_provider"
            ) as mock_get_llm_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
        ):
            mock_llm_provider = Mock()
            mock_llm_provider.get_llm_model.return_value = Mock()
            mock_get_llm_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = Mock()

            result = get_custom_model("gpt-4")

            mock_llm_provider.get_llm_model.assert_called_once_with("gpt-4")
            assert result is not None

    def test_get_chat_history(self):
        from langchain_core.runnables import RunnableConfig

        config = RunnableConfig(
            configurable={"chat_history": [{"role": "user", "content": "test"}]}
        )

        result = get_chat_history(config)

        assert result == [{"role": "user", "content": "test"}]

    def test_get_chat_history_default(self):
        from langchain_core.runnables import RunnableConfig

        config = RunnableConfig()

        result = get_chat_history(config)

        assert result == []
