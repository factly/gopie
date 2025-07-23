from unittest.mock import Mock, patch

from portkey_ai import PORTKEY_GATEWAY_URL

from app.utils.providers.embedding_providers.custom import (
    CustomEmbeddingProvider,
)
from app.utils.providers.embedding_providers.litellm import (
    LiteLLMEmbeddingProvider,
)
from app.utils.providers.embedding_providers.openai import (
    OpenAIEmbeddingProvider,
)
from app.utils.providers.embedding_providers.portkey import (
    PortkeyEmbeddingProvider,
)


class TestPortkeyEmbeddingProvider:
    def test_portkey_embedding_provider_initialization(self, sample_metadata):
        provider = PortkeyEmbeddingProvider(sample_metadata.copy())

        assert provider.user == "test_user"
        assert provider.trace_id == "test_trace_123"
        assert provider.chat_id == "test_chat_456"

    def test_get_headers(self, sample_metadata):
        """
        Tests that PortkeyEmbeddingProvider.get_headers() calls createHeaders with the correct arguments and returns the expected headers dictionary.
        """
        with (
            patch("app.utils.providers.embedding_providers.portkey.settings") as mock_settings,
            patch(
                "app.utils.providers.embedding_providers.portkey.createHeaders"
            ) as mock_create_headers,
        ):

            mock_settings.PORTKEY_API_KEY = "test_api_key"
            mock_settings.PORTKEY_EMBEDDING_PROVIDER_API_KEY = None
            mock_settings.PORTKEY_EMBEDDING_PROVIDER_NAME = None
            mock_settings.PORTKEY_URL = None
            mock_create_headers.return_value = {"Authorization": "Bearer test"}

            provider = PortkeyEmbeddingProvider(sample_metadata.copy())
            result = provider.get_headers()

            mock_create_headers.assert_called_once_with(
                api_key="test_api_key",
                trace_id="test_trace_123",
                chat_id="test_chat_456",
                metadata={
                    "_user": "test_user",
                },
            )
            assert result == {"Authorization": "Bearer test"}

    def test_get_embeddings_model(self, sample_metadata):
        """
        Tests that PortkeyEmbeddingProvider.get_embeddings_model returns an embeddings model instance with the correct parameters.

        Verifies that the OpenAIEmbeddings class is called with the expected API key, base URL, headers, and model name, and that the returned object matches the mocked embeddings model.
        """
        with (
            patch("app.utils.providers.embedding_providers.portkey.settings") as mock_settings,
            patch(
                "app.utils.providers.embedding_providers.portkey.OpenAIEmbeddings"
            ) as mock_embeddings,
            patch(
                "app.utils.providers.embedding_providers.portkey.createHeaders"
            ) as mock_create_headers,
            patch(
                "app.utils.providers.embedding_providers.portkey.PORTKEY_GATEWAY_URL",
                PORTKEY_GATEWAY_URL,
            ),
        ):

            mock_settings.PORTKEY_API_KEY = "test_key"
            mock_settings.PORTKEY_EMBEDDING_PROVIDER_API_KEY = None
            mock_settings.PORTKEY_EMBEDDING_PROVIDER_NAME = None
            mock_settings.PORTKEY_URL = None
            mock_create_headers.return_value = {"test": "headers"}
            mock_model = Mock()
            mock_embeddings.return_value = mock_model

            provider = PortkeyEmbeddingProvider(sample_metadata.copy())
            result = provider.get_embeddings_model("text-embedding-ada-002")

            mock_embeddings.assert_called_once_with(
                api_key="X",
                base_url=PORTKEY_GATEWAY_URL,
                default_headers={"test": "headers"},
                model="text-embedding-ada-002",
            )
            assert result == mock_model

    def test_self_hosted_provider_initialization(self, sample_metadata):
        """
        Tests that PortkeyEmbeddingProvider initializes correctly in a self-hosted configuration.

        Verifies that the provider extracts user, trace ID, and chat ID from metadata, sets self_hosted to True, and assigns the provider API key from settings.
        """
        with patch("app.utils.providers.embedding_providers.portkey.settings") as mock_settings:
            mock_settings.PORTKEY_API_KEY = "test_key"
            mock_settings.PORTKEY_EMBEDDING_PROVIDER_API_KEY = "provider_key"
            mock_settings.PORTKEY_EMBEDDING_PROVIDER_NAME = "test_provider"
            mock_settings.PORTKEY_URL = "https://self-hosted.portkey.ai"

            provider = PortkeyEmbeddingProvider(sample_metadata)

            assert provider.user == "test_user"
            assert provider.trace_id == "test_trace_123"
            assert provider.chat_id == "test_chat_456"
            assert provider.self_hosted is True
            assert provider.provider_api_key == "provider_key"


class TestLiteLLMEmbeddingProvider:
    def test_litellm_provider_initialization(self, sample_metadata):
        """
        Tests that LiteLLMEmbeddingProvider initializes with the provided metadata and sets the correct authorization header using the master key from settings.
        """
        with patch("app.utils.providers.embedding_providers.litellm.settings") as mock_settings:
            mock_settings.LITELLM_MASTER_KEY = "master_key_123"
            mock_settings.LITELLM_KEY_HEADER_NAME = None
            mock_settings.LITELLM_VIRTUAL_KEY = None

            provider = LiteLLMEmbeddingProvider(sample_metadata)

            assert provider.metadata == sample_metadata
            assert provider.headers == {"Authorization": "Bearer master_key_123"}

    def test_get_embeddings_model(self, sample_metadata):
        """
        Tests that LiteLLMEmbeddingProvider.get_embeddings_model returns an embeddings model initialized with the correct API key, base URL, headers, and model name using mocked settings and dependencies.
        """
        with (
            patch("app.utils.providers.embedding_providers.litellm.settings") as mock_settings,
            patch(
                "app.utils.providers.embedding_providers.litellm.OpenAIEmbeddings"
            ) as mock_embeddings,
        ):

            mock_settings.LITELLM_MASTER_KEY = "master_key"
            mock_settings.LITELLM_BASE_URL = "https://litellm.example.com"

            provider = LiteLLMEmbeddingProvider(sample_metadata)
            result = provider.get_embeddings_model("text-embedding-ada-002")

            mock_embeddings.assert_called_once_with(
                api_key="X",
                base_url="https://litellm.example.com",
                default_headers={"Authorization": "Bearer master_key"},
                model="text-embedding-ada-002",
            )
            assert result == mock_embeddings.return_value


class TestOpenAIEmbeddingProvider:
    def test_get_embeddings_model(self, sample_metadata):
        """
        Test that OpenAIEmbeddingProvider.get_embeddings_model returns an OpenAIEmbeddings instance with the correct API key and model name.
        """
        with (
            patch("app.utils.providers.embedding_providers.openai.settings") as mock_settings,
            patch(
                "app.utils.providers.embedding_providers.openai.OpenAIEmbeddings"
            ) as mock_embeddings,
        ):

            mock_settings.OPENAI_API_KEY = "openai_key"
            mock_model = Mock()
            mock_embeddings.return_value = mock_model

            provider = OpenAIEmbeddingProvider(sample_metadata)
            result = provider.get_embeddings_model("text-embedding-ada-002")

            mock_embeddings.assert_called_once_with(
                api_key="openai_key",
                model="text-embedding-ada-002",
            )
            assert result == mock_model


class TestCustomEmbeddingProvider:
    def test_get_embeddings_model(self, sample_metadata):
        """
        Tests that CustomEmbeddingProvider.get_embeddings_model returns an embedding model initialized with the custom API key, base URL, and specified model name.
        """
        with patch("app.utils.providers.embedding_providers.custom.settings") as mock_settings:
            mock_settings.CUSTOM_EMBEDDING_API_KEY = "custom_key"
            mock_settings.CUSTOM_EMBEDDING_BASE_URL = "https://custom.api"

            provider = CustomEmbeddingProvider(sample_metadata)

            with patch(
                "app.utils.providers.embedding_providers.custom.OpenAIEmbeddings"
            ) as mock_embeddings:
                mock_model = Mock()
                mock_embeddings.return_value = mock_model

                result = provider.get_embeddings_model("text-embedding-ada-002")

                mock_embeddings.assert_called_once_with(
                    base_url="https://custom.api",
                    api_key="custom_key",
                    model="text-embedding-ada-002",
                )
                assert result == mock_model
