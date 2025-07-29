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
        """
        Test that `get_llm_provider` returns a `PortkeyLLMProvider` instance when the LLM gateway provider is set to "portkey".
        """
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.LLM_GATEWAY_PROVIDER = "portkey"

            provider = get_llm_provider(sample_metadata)

            from app.utils.providers.llm_providers.portkey import (
                PortkeyLLMProvider,
            )

            assert isinstance(provider, PortkeyLLMProvider)

    def test_get_llm_provider_litellm(self, sample_metadata):
        """
        Test that `get_llm_provider` returns a `LiteLLMProvider` instance when the LLM gateway provider is set to 'litellm'.
        """
        with (
            patch("app.utils.model_registry.model_provider.settings") as mock_settings,
            patch("app.utils.providers.llm_providers.litellm.settings") as mock_litellm_settings,
        ):
            mock_settings.LLM_GATEWAY_PROVIDER = "litellm"
            mock_litellm_settings.LITELLM_MASTER_KEY = "test_master_key"
            mock_litellm_settings.LITELLM_VIRTUAL_KEY = None
            mock_litellm_settings.LITELLM_KEY_HEADER_NAME = None

            provider = get_llm_provider(sample_metadata)

            from app.utils.providers.llm_providers.litellm import (
                LiteLLMProvider,
            )

            assert isinstance(provider, LiteLLMProvider)

    def test_get_llm_provider_cloudflare(self, sample_metadata):
        """
        Test that `get_llm_provider` returns a `CloudflareLLMProvider` instance when the LLM gateway provider is set to 'cloudflare'.
        """
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.LLM_GATEWAY_PROVIDER = "cloudflare"

            provider = get_llm_provider(sample_metadata)

            from app.utils.providers.llm_providers.cloudflare import (
                CloudflareLLMProvider,
            )

            assert isinstance(provider, CloudflareLLMProvider)

    def test_get_llm_provider_openrouter(self, sample_metadata):
        """
        Test that `get_llm_provider` returns an `OpenRouterLLMProvider` instance when the LLM gateway provider is set to 'openrouter'.
        """
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.LLM_GATEWAY_PROVIDER = "openrouter"

            provider = get_llm_provider(sample_metadata)

            from app.utils.providers.llm_providers.openrouter import (
                OpenRouterLLMProvider,
            )

            assert isinstance(provider, OpenRouterLLMProvider)

    def test_get_llm_provider_custom(self, sample_metadata):
        """
        Test that `get_llm_provider` returns a `CustomLLMProvider` instance when the LLM gateway provider is set to 'custom'.
        """
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.LLM_GATEWAY_PROVIDER = "custom"

            provider = get_llm_provider(sample_metadata)

            from app.utils.providers.llm_providers.custom import (
                CustomLLMProvider,
            )

            assert isinstance(provider, CustomLLMProvider)


class TestEmbeddingProvider:
    def test_get_embedding_provider_portkey(self, sample_metadata):
        """
        Test that the Portkey embedding provider is returned when the EMBEDDING_GATEWAY_PROVIDER setting is set to 'portkey'.
        """
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.EMBEDDING_GATEWAY_PROVIDER = "portkey"

            provider = get_embedding_provider(sample_metadata)

            from app.utils.providers.embedding_providers.portkey import (
                PortkeyEmbeddingProvider,
            )

            assert isinstance(provider, PortkeyEmbeddingProvider)

    def test_get_embedding_provider_litellm(self, sample_metadata):
        """
        Test that `get_embedding_provider` returns a `LiteLLMEmbeddingProvider` instance when the embedding gateway provider is set to 'litellm'.
        """
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.EMBEDDING_GATEWAY_PROVIDER = "litellm"

            provider = get_embedding_provider(sample_metadata)

            from app.utils.providers.embedding_providers.litellm import (
                LiteLLMEmbeddingProvider,
            )

            assert isinstance(provider, LiteLLMEmbeddingProvider)

    def test_get_embedding_provider_openai(self, sample_metadata):
        """
        Test that `get_embedding_provider` returns an `OpenAIEmbeddingProvider` instance when the embedding gateway provider is set to 'openai'.
        """
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.EMBEDDING_GATEWAY_PROVIDER = "openai"

            provider = get_embedding_provider(sample_metadata)

            from app.utils.providers.embedding_providers.openai import (
                OpenAIEmbeddingProvider,
            )

            assert isinstance(provider, OpenAIEmbeddingProvider)

    def test_get_embedding_provider_custom(self, sample_metadata):
        """
        Test that `get_embedding_provider` returns a `CustomEmbeddingProvider` instance when the embedding gateway provider is set to 'custom'.
        """
        with patch("app.utils.model_registry.model_provider.settings") as mock_settings:
            mock_settings.EMBEDDING_GATEWAY_PROVIDER = "custom"

            provider = get_embedding_provider(sample_metadata)

            from app.utils.providers.embedding_providers.custom import (
                CustomEmbeddingProvider,
            )

            assert isinstance(provider, CustomEmbeddingProvider)


class TestModelProvider:
    @pytest.fixture
    def mock_llm_provider(self):
        """
        Return a mock LLM provider with a stubbed `get_llm_model` method for use in tests.
        """
        return Mock(
            get_llm_model=Mock(return_value=Mock()),
        )

    @pytest.fixture
    def mock_embedding_provider(self):
        return Mock(
            get_embeddings_model=Mock(return_value=Mock()),
        )

    def test_model_provider_initialization(self, sample_metadata):
        """
        Test that ModelProvider initializes with the correct metadata and provider instances.

        Verifies that the ModelProvider's attributes are set to the provided metadata and the mocked LLM and embedding providers.
        """
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
        """
        Test that ModelProvider._create_llm correctly retrieves an LLM model using the provided model ID.

        Verifies that the LLM provider's get_llm_model method is called with the specified model ID and that a non-null model is returned.
        """
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
        """
        Test that ModelProvider correctly creates an LLM model with tools bound to it.

        Verifies that the LLM provider's `get_llm_model` method is called with the specified model ID, the appropriate tools are fetched and bound to the model, and the resulting model is not None.
        """
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
        """
        Test that `ModelProvider.get_llm_for_node` retrieves the correct LLM model for a node when no tools are provided.

        Verifies that the node model ID is resolved, the LLM provider's `get_llm_model` is called with the correct model ID, and a non-null model is returned.
        """
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
        """
        Test that `ModelProvider.get_llm_for_node` correctly retrieves and binds tools to the LLM model for a given node.

        Verifies that the appropriate provider and utility functions are called with the correct arguments, tools are fetched and bound to the LLM model, and the resulting model is not None.
        """
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
        """
        Test that ModelProvider._create_embeddings_model returns an embeddings model using the default embedding model ID.

        Verifies that the embedding provider's get_embeddings_model method is called with the expected default model and that a non-null result is returned.
        """
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
        """
        Test that `get_model_provider` returns a `ModelProvider` instance with the correct metadata extracted from a `RunnableConfig`.
        """
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
        """
        Test that `get_custom_model` retrieves an LLM model using the specified model ID.

        Verifies that the LLM provider's `get_llm_model` method is called with the correct model ID and that a non-null model is returned.
        """
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
        """
        Test that `get_chat_history` correctly extracts the chat history from a `RunnableConfig` object.
        """
        from langchain_core.runnables import RunnableConfig

        config = RunnableConfig(
            configurable={"chat_history": [{"role": "user", "content": "test"}]}
        )

        result = get_chat_history(config)

        assert result == [{"role": "user", "content": "test"}]

    def test_get_chat_history_default(self):
        """
        Test that `get_chat_history` returns an empty list when no chat history is present in the configuration.
        """
        from langchain_core.runnables import RunnableConfig

        config = RunnableConfig()

        result = get_chat_history(config)

        assert result == []
