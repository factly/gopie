from unittest.mock import Mock, patch

from app.utils.embedding_providers.base import BaseEmbeddingProvider
from app.utils.embedding_providers.custom import CustomEmbeddingProvider
from app.utils.embedding_providers.litellm import LiteLLMEmbeddingProvider
from app.utils.embedding_providers.openai import OpenAIEmbeddingProvider
from app.utils.embedding_providers.portkey import PortkeyEmbeddingProvider
from app.utils.embedding_providers.portkey_self_hosted import (
    PortkeySelfHostedEmbeddingProvider,
)


class TestPortkeyEmbeddingProvider:
    def test_portkey_embedding_provider_initialization(self, sample_metadata):
        provider = PortkeyEmbeddingProvider(sample_metadata.copy())

        assert provider.user == "test_user"
        assert provider.trace_id == "test_trace_123"
        assert provider.chat_id == "test_chat_456"

    def test_get_headers(self, sample_metadata):
        with (
            patch(
                "app.utils.embedding_providers.portkey.settings"
            ) as mock_settings,
            patch(
                "app.utils.embedding_providers.portkey.createHeaders"
            ) as mock_create_headers,
        ):

            mock_settings.PORTKEY_API_KEY = "test_api_key"
            mock_create_headers.return_value = {"Authorization": "Bearer test"}

            provider = PortkeyEmbeddingProvider(sample_metadata.copy())
            result = provider.get_headers("virtual_key_123")

            mock_create_headers.assert_called_once_with(
                api_key="test_api_key",
                virtual_key="virtual_key_123",
                trace_id="test_trace_123",
                chat_id="test_chat_456",
                metadata={
                    "_user": "test_user",
                },
            )
            assert result == {"Authorization": "Bearer test"}

    def test_get_embeddings_model(self, sample_metadata):
        with (
            patch(
                "app.utils.embedding_providers.portkey.settings"
            ) as mock_settings,
            patch(
                "app.utils.embedding_providers.portkey.OpenAIEmbeddings"
            ) as mock_embeddings,
            patch(
                "app.utils.embedding_providers.portkey.createHeaders"
            ) as mock_create_headers,
            patch(
                "app.utils.embedding_providers.portkey.PORTKEY_GATEWAY_URL",
                "https://api.portkey.ai",
            ),
        ):

            mock_settings.PORTKEY_API_KEY = "test_key"
            mock_settings.OPENAI_VIRTUAL_KEY = "openai_vkey"
            mock_create_headers.return_value = {"test": "headers"}
            mock_model = Mock()
            mock_embeddings.return_value = mock_model

            provider = PortkeyEmbeddingProvider(sample_metadata.copy())
            result = provider.get_embeddings_model("text-embedding-ada-002")

            mock_embeddings.assert_called_once_with(
                api_key="X",
                base_url="https://api.portkey.ai",
                default_headers={"test": "headers"},
                model="text-embedding-ada-002",
            )
            assert result == mock_model


class TestPortkeySelfHostedEmbeddingProvider:
    def test_portkey_self_hosted_provider_initialization(
        self, sample_metadata
    ):
        provider = PortkeySelfHostedEmbeddingProvider(sample_metadata)

        assert provider.user == "test_user"
        assert provider.trace_id == "test_trace_123"
        assert provider.chat_id == "test_chat_456"
        assert "test_user" in provider.headers["x-portkey-metadata"]

    def test_get_embeddings_model(self, sample_metadata):
        with (
            patch(
                "app.utils.embedding_providers.portkey_self_hosted.settings"
            ) as mock_settings,
            patch(
                "app.utils.embedding_providers.portkey_self_hosted.OpenAIEmbeddings"
            ) as mock_embeddings,
        ):
            mock_settings.PORTKEY_SELF_HOSTED_URL = (
                "https://self-hosted.portkey.ai"
            )
            mock_model = Mock()
            mock_embeddings.return_value = mock_model

            provider = PortkeySelfHostedEmbeddingProvider(sample_metadata)
            result = provider.get_embeddings_model("text-embedding-ada-002")

            mock_embeddings.assert_called_once()
            assert result == mock_model


class TestLiteLLMEmbeddingProvider:
    def test_litellm_provider_initialization(self, sample_metadata):
        with patch(
            "app.utils.embedding_providers.litellm.settings"
        ) as mock_settings:
            mock_settings.LITELLM_MASTER_KEY = "master_key_123"

            provider = LiteLLMEmbeddingProvider(sample_metadata)

            assert provider.metadata == sample_metadata
            assert provider.headers == {
                "Authorization": "Bearer master_key_123"
            }

    def test_get_embeddings_model(self, sample_metadata):
        with (
            patch(
                "app.utils.embedding_providers.litellm.settings"
            ) as mock_settings,
            patch(
                "app.utils.embedding_providers.litellm.OpenAIEmbeddings"
            ) as mock_embeddings,
        ):

            mock_settings.LITELLM_MASTER_KEY = "master_key"
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_model = Mock()
            mock_embeddings.return_value = mock_model

            provider = LiteLLMEmbeddingProvider(sample_metadata)
            result = provider.get_embeddings_model("text-embedding-ada-002")

            mock_embeddings.assert_called_once_with(
                api_key="X",
                base_url="http://localhost:4000",
                default_headers={"Authorization": "Bearer master_key"},
                model="text-embedding-ada-002",
            )
            assert result == mock_model


class TestOpenAIEmbeddingProvider:
    def test_openai_provider_initialization(self, sample_metadata):
        provider = OpenAIEmbeddingProvider(sample_metadata)

        # The provider doesn't actually store metadata, so we just check it initializes
        assert isinstance(provider, BaseEmbeddingProvider)

    def test_get_embeddings_model(self, sample_metadata):
        with (
            patch(
                "app.utils.embedding_providers.openai.settings"
            ) as mock_settings,
            patch(
                "app.utils.embedding_providers.openai.OpenAIEmbeddings"
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
    def test_custom_provider_initialization(self, sample_metadata):
        provider = CustomEmbeddingProvider(sample_metadata)

        # The provider doesn't actually store metadata, so we just check it initializes
        assert isinstance(provider, BaseEmbeddingProvider)

    def test_get_embeddings_model(self, sample_metadata):
        with patch(
            "app.utils.embedding_providers.custom.settings"
        ) as mock_settings:
            mock_settings.CUSTOM_EMBEDDING_API_KEY = "custom_key"
            mock_settings.CUSTOM_EMBEDDING_BASE_URL = "https://custom.api"

            provider = CustomEmbeddingProvider(sample_metadata)

            with patch(
                "app.utils.embedding_providers.custom.OpenAIEmbeddings"
            ) as mock_embeddings:
                mock_model = Mock()
                mock_embeddings.return_value = mock_model

                result = provider.get_embeddings_model(
                    "text-embedding-ada-002"
                )

                mock_embeddings.assert_called_once_with(
                    base_url="https://custom.api",
                    api_key="custom_key",
                    model="text-embedding-ada-002",
                )
                assert result == mock_model
