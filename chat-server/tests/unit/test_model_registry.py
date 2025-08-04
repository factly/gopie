from typing import Type
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel, Field

from app.tool_utils.tools import ToolNames
from app.utils.model_registry.model_provider import (
    ModelProvider,
    get_chat_history,
    get_configured_llm_for_node,
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
            assert model_provider.json_mode is False
            assert model_provider.temperature is None
            assert model_provider.schema is None

    def test_model_provider_initialization_with_parameters(self, sample_metadata):
        """
        Test that ModelProvider initializes with custom parameters.
        """

        class TestSchema(BaseModel):
            test_field: str = Field(description="Test field")

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

            model_provider = ModelProvider(
                sample_metadata, json_mode=True, temperature=0.7, schema=TestSchema
            )

            assert model_provider.json_mode is True
            assert model_provider.temperature == 0.7
            assert model_provider.schema == TestSchema

    def test_create_llm_model(self, sample_metadata, mock_llm_provider):
        """
        Test that ModelProvider._create_llm correctly retrieves an LLM model using the provided model ID.

        Verifies that the LLM provider's get_llm_model method is called with the specified model ID and configuration parameters.
        """
        with (
            patch("app.utils.model_registry.model_provider.get_llm_provider") as mock_get_provider,
            patch(
                "app.utils.model_registry.model_provider.get_embedding_provider"
            ) as mock_get_embedding_provider,
        ):

            mock_get_provider.return_value = mock_llm_provider
            mock_get_embedding_provider.return_value = Mock()

            model_provider = ModelProvider(sample_metadata, temperature=0.8, json_mode=True)
            result = model_provider._create_llm("gpt-4")

            mock_llm_provider.get_llm_model.assert_called_once_with(
                "gpt-4", temperature=0.8, json_mode=True, schema=None
            )
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

            mock_llm_provider.get_llm_model.assert_called_once_with(
                "gpt-4", temperature=None, json_mode=False, schema=None
            )
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
            mock_llm_provider.get_llm_model.assert_called_once_with(
                "gpt-4", temperature=None, json_mode=False, schema=None
            )
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

            # get_node_model is called once for the node
            mock_get_node_model.assert_called_with("test_node")
            mock_llm_provider.get_llm_model.assert_called_once_with(
                "gpt-4", temperature=None, json_mode=False, schema=None
            )
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
            assert result.json_mode is False
            assert result.temperature is None
            assert result.schema is None

    def test_get_model_provider_with_parameters(self):
        """
        Test that `get_model_provider` correctly passes additional parameters to ModelProvider.
        """
        from langchain_core.runnables import RunnableConfig

        class TestSchema(BaseModel):
            test_field: str = Field(description="Test field")

        config = RunnableConfig(configurable={"metadata": {"user": "test_user"}})

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

            result = get_model_provider(config, json_mode=True, temperature=0.5, schema=TestSchema)

            assert result.json_mode is True
            assert result.temperature == 0.5
            assert result.schema == TestSchema

    def test_get_configured_llm_for_node(self):
        """
        Test that `get_configured_llm_for_node` returns a properly configured LLM with type inference.
        """
        from langchain_core.runnables import RunnableConfig

        class TestOutput(BaseModel):
            result: str = Field(description="Test result")

        config = RunnableConfig(configurable={"metadata": {"user": "test_user"}})

        mock_llm = Mock()

        with (
            patch(
                "app.utils.model_registry.model_provider.get_model_provider"
            ) as mock_get_model_provider,
            patch(
                "app.utils.model_registry.model_provider.requires_json_mode"
            ) as mock_requires_json_mode,
            patch(
                "app.utils.model_registry.model_provider.get_node_temperature"
            ) as mock_get_node_temperature,
        ):
            mock_model_provider = Mock()
            mock_model_provider.get_llm_for_node.return_value = mock_llm
            mock_get_model_provider.return_value = mock_model_provider
            mock_requires_json_mode.return_value = True
            mock_get_node_temperature.return_value = 0.7

            result = get_configured_llm_for_node("test_node", config, schema=TestOutput)

            mock_requires_json_mode.assert_called_once_with("test_node")
            mock_get_node_temperature.assert_called_once_with("test_node")
            mock_get_model_provider.assert_called_once_with(
                config, json_mode=True, temperature=0.7, schema=TestOutput
            )
            mock_model_provider.get_llm_for_node.assert_called_once_with("test_node", None)

            # Verify the returned type is cast to StructuredLLM
            assert result == mock_llm

    def test_get_configured_llm_for_node_with_tools(self):
        """
        Test that `get_configured_llm_for_node` correctly passes tools to the model provider.
        """
        from langchain_core.runnables import RunnableConfig

        config = RunnableConfig()
        mock_llm = Mock()

        with (
            patch(
                "app.utils.model_registry.model_provider.get_model_provider"
            ) as mock_get_model_provider,
            patch(
                "app.utils.model_registry.model_provider.requires_json_mode"
            ) as mock_requires_json_mode,
            patch(
                "app.utils.model_registry.model_provider.get_node_temperature"
            ) as mock_get_node_temperature,
        ):
            mock_model_provider = Mock()
            mock_model_provider.get_llm_for_node.return_value = mock_llm
            mock_get_model_provider.return_value = mock_model_provider
            mock_requires_json_mode.return_value = False
            mock_get_node_temperature.return_value = None

            result = get_configured_llm_for_node(
                "test_node", config, tool_names=[ToolNames.EXECUTE_SQL_QUERY]
            )

            mock_model_provider.get_llm_for_node.assert_called_once_with(
                "test_node", [ToolNames.EXECUTE_SQL_QUERY]
            )
            assert result == mock_llm

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
