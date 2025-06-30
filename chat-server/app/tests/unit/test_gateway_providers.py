"""Tests for gateway providers."""

from unittest.mock import Mock, patch

import pytest

from app.utils.providers.cloudflare import CloudflareGatewayProvider
from app.utils.providers.litellm import LiteLLMGatewayProvider
from app.utils.providers.openrouter import OpenrouterGatewayProvider
from app.utils.providers.portkey import PortkeyGatewayProvider


class TestPortkeyGatewayProvider:
    """Test cases for Portkey gateway provider."""

    @pytest.fixture
    def provider_metadata(self):
        """Sample provider metadata."""
        return {
            "user": "test_user",
            "trace_id": "trace_123",
            "chat_id": "chat_456",
            "project_id": "proj_789",
        }

    def test_portkey_provider_initialization(self, provider_metadata):
        """Test Portkey provider initialization."""
        provider = PortkeyGatewayProvider(provider_metadata.copy())

        assert provider.user == "test_user"
        assert provider.trace_id == "trace_123"
        assert provider.chat_id == "chat_456"
        assert provider.metadata == {"project_id": "proj_789"}

    def test_portkey_provider_initialization_with_defaults(self):
        """Test Portkey provider initialization with default values."""
        provider = PortkeyGatewayProvider({})

        assert provider.user == ""
        assert provider.trace_id == ""
        assert provider.chat_id == ""
        assert provider.metadata == {}

    def test_get_headers(self, provider_metadata):
        """Test get_headers method."""
        with (
            patch("app.utils.providers.portkey.settings") as mock_settings,
            patch(
                "app.utils.providers.portkey.createHeaders"
            ) as mock_create_headers,
        ):

            mock_settings.PORTKEY_API_KEY = "test_api_key"
            mock_create_headers.return_value = {"Authorization": "Bearer test"}

            provider = PortkeyGatewayProvider(provider_metadata.copy())
            result = provider.get_headers("virtual_key_123")

            mock_create_headers.assert_called_once_with(
                api_key="test_api_key",
                virtual_key="virtual_key_123",
                trace_id="trace_123",
                chat_id="chat_456",
                metadata={
                    "_user": "test_user",
                    "project_id": "proj_789",
                },
            )
            assert result == {"Authorization": "Bearer test"}

    def test_get_openai_model(self, provider_metadata):
        """Test get_openai_model method."""
        with (
            patch("app.utils.providers.portkey.settings") as mock_settings,
            patch(
                "app.utils.providers.portkey.ChatOpenAI"
            ) as mock_chat_openai,
            patch(
                "app.utils.providers.portkey.createHeaders"
            ) as mock_create_headers,
            patch(
                "app.utils.providers.portkey.PORTKEY_GATEWAY_URL",
                "https://api.portkey.ai",
            ),
        ):

            mock_settings.PORTKEY_API_KEY = "test_key"
            mock_settings.OPENAI_VIRTUAL_KEY = "openai_vkey"
            mock_create_headers.return_value = {"test": "headers"}
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = PortkeyGatewayProvider(provider_metadata.copy())
            result = provider.get_openai_model("gpt-4")

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url="https://api.portkey.ai",
                default_headers={"test": "headers"},
                model="gpt-4",
                streaming=True,
            )
            assert result == mock_model

    def test_get_gemini_model(self, provider_metadata):
        """Test get_gemini_model method."""
        with (
            patch("app.utils.providers.portkey.settings") as mock_settings,
            patch(
                "app.utils.providers.portkey.ChatOpenAI"
            ) as mock_chat_openai,
            patch(
                "app.utils.providers.portkey.createHeaders"
            ) as mock_create_headers,
            patch(
                "app.utils.providers.portkey.PORTKEY_GATEWAY_URL",
                "https://api.portkey.ai",
            ),
        ):

            mock_settings.PORTKEY_API_KEY = "test_key"
            mock_settings.GEMINI_VIRTUAL_KEY = "gemini_vkey"
            mock_create_headers.return_value = {"test": "headers"}
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = PortkeyGatewayProvider(provider_metadata.copy())
            result = provider.get_gemini_model("gemini-pro", streaming=False)

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url="https://api.portkey.ai",
                default_headers={"test": "headers"},
                model="gemini-pro",
                streaming=False,
            )
            assert result == mock_model

    def test_get_embeddings_model(self, provider_metadata):
        """Test get_embeddings_model method."""
        with (
            patch("app.utils.providers.portkey.settings") as mock_settings,
            patch(
                "app.utils.providers.portkey.OpenAIEmbeddings"
            ) as mock_embeddings,
            patch(
                "app.utils.providers.portkey.createHeaders"
            ) as mock_create_headers,
            patch(
                "app.utils.providers.portkey.PORTKEY_GATEWAY_URL",
                "https://api.portkey.ai",
            ),
        ):

            mock_settings.PORTKEY_API_KEY = "test_key"
            mock_settings.OPENAI_VIRTUAL_KEY = "openai_vkey"
            mock_create_headers.return_value = {"test": "headers"}
            mock_model = Mock()
            mock_embeddings.return_value = mock_model

            provider = PortkeyGatewayProvider(provider_metadata.copy())
            result = provider.get_embeddings_model("text-embedding-ada-002")

            mock_embeddings.assert_called_once_with(
                api_key="X",
                base_url="https://api.portkey.ai",
                default_headers={"test": "headers"},
                model="text-embedding-ada-002",
            )
            assert result == mock_model


class TestLiteLLMGatewayProvider:
    """Test cases for LiteLLM gateway provider."""

    @pytest.fixture
    def provider_metadata(self):
        """Sample provider metadata."""
        return {
            "user": "test_user",
            "project_id": "proj_123",
        }

    def test_litellm_provider_initialization(self, provider_metadata):
        """Test LiteLLM provider initialization."""
        with patch("app.utils.providers.litellm.settings") as mock_settings:
            mock_settings.LITELLM_MASTER_KEY = "master_key_123"

            provider = LiteLLMGatewayProvider(provider_metadata)

            assert provider.metadata == provider_metadata
            assert provider.headers == {
                "Authorization": "Bearer master_key_123"
            }

    def test_get_openai_model(self, provider_metadata):
        """Test get_openai_model method."""
        with (
            patch("app.utils.providers.litellm.settings") as mock_settings,
            patch(
                "app.utils.providers.litellm.ChatOpenAI"
            ) as mock_chat_openai,
        ):

            mock_settings.LITELLM_MASTER_KEY = "master_key"
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = LiteLLMGatewayProvider(provider_metadata)
            result = provider.get_openai_model("gpt-4")

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url="http://localhost:4000",
                model="gpt-4",
                default_headers={"Authorization": "Bearer master_key"},
                streaming=True,
                extra_body={"metadata": provider_metadata},
            )
            assert result == mock_model

    def test_get_gemini_model(self, provider_metadata):
        """Test get_gemini_model method."""
        with (
            patch("app.utils.providers.litellm.settings") as mock_settings,
            patch(
                "app.utils.providers.litellm.ChatOpenAI"
            ) as mock_chat_openai,
        ):

            mock_settings.LITELLM_MASTER_KEY = "master_key"
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = LiteLLMGatewayProvider(provider_metadata)
            result = provider.get_gemini_model("gemini-pro", streaming=False)

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url="http://localhost:4000",
                model="gemini-pro",
                default_headers={"Authorization": "Bearer master_key"},
                streaming=False,
                extra_body={"metadata": provider_metadata},
            )
            assert result == mock_model

    def test_get_embeddings_model(self, provider_metadata):
        """Test get_embeddings_model method."""
        with (
            patch("app.utils.providers.litellm.settings") as mock_settings,
            patch(
                "app.utils.providers.litellm.OpenAIEmbeddings"
            ) as mock_embeddings,
        ):

            mock_settings.LITELLM_MASTER_KEY = "master_key"
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_model = Mock()
            mock_embeddings.return_value = mock_model

            provider = LiteLLMGatewayProvider(provider_metadata)
            result = provider.get_embeddings_model("text-embedding-ada-002")

            mock_embeddings.assert_called_once_with(
                api_key="X",
                base_url="http://localhost:4000",
                default_headers={"Authorization": "Bearer master_key"},
                model="text-embedding-ada-002",
            )
            assert result == mock_model


class TestOpenrouterGatewayProvider:
    """Test cases for OpenRouter gateway provider."""

    @pytest.fixture
    def provider_metadata(self):
        """Sample provider metadata."""
        return {"user": "test_user"}

    def test_openrouter_provider_initialization(self, provider_metadata):
        """Test OpenRouter provider initialization."""
        provider = OpenrouterGatewayProvider(provider_metadata)

        assert provider.metadata == provider_metadata

    def test_get_openai_model(self, provider_metadata):
        """Test get_openai_model method."""
        with (
            patch("app.utils.providers.openrouter.settings") as mock_settings,
            patch(
                "app.utils.providers.openrouter.ChatOpenAI"
            ) as mock_chat_openai,
        ):

            mock_settings.OPENROUTER_API_KEY = "openrouter_key"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = OpenrouterGatewayProvider(provider_metadata)
            result = provider.get_openai_model("gpt-4")

            mock_chat_openai.assert_called_once_with(
                api_key="openrouter_key",
                base_url=mock_settings.OPENROUTER_BASE_URL,
                model="openai/gpt-4",
                metadata=provider_metadata,
            )
            assert result == mock_model

    def test_get_embeddings_model(self, provider_metadata):
        """Test get_embeddings_model method."""
        with (
            patch("app.utils.providers.openrouter.settings") as mock_settings,
            patch(
                "app.utils.providers.openrouter.OpenAIEmbeddings"
            ) as mock_embeddings,
        ):

            mock_settings.OPENROUTER_API_KEY = "openrouter_key"
            mock_model = Mock()
            mock_embeddings.return_value = mock_model

            provider = OpenrouterGatewayProvider(provider_metadata)
            result = provider.get_embeddings_model("text-embedding-ada-002")

            mock_embeddings.assert_called_once_with(
                api_key="openrouter_key",
                base_url=mock_settings.OPENROUTER_BASE_URL,
                model="openai/text-embedding-ada-002",
            )
            assert result == mock_model


class TestCloudflareGatewayProvider:
    """Test cases for Cloudflare gateway provider."""

    @pytest.fixture
    def provider_metadata(self):
        """Sample provider metadata."""
        return {"user": "test_user"}

    def test_cloudflare_provider_initialization(self, provider_metadata):
        """Test Cloudflare provider initialization."""
        provider = CloudflareGatewayProvider(provider_metadata)

        assert provider.metadata == provider_metadata

    def test_get_openai_model(self, provider_metadata):
        """Test get_openai_model method."""
        with (
            patch("app.utils.providers.cloudflare.settings") as mock_settings,
            patch(
                "app.utils.providers.cloudflare.ChatOpenAI"
            ) as mock_chat_openai,
        ):

            mock_settings.CLOUDFLARE_API_TOKEN = "cloudflare_token"
            mock_settings.CLOUDFLARE_GATEWAY_URL = (
                "https://gateway.example.com/{account_id}/{gateway_id}/ai/v1"
            )
            mock_settings.CLOUDFLARE_ACCOUNT_ID = "account_123"
            mock_settings.CLOUDFLARE_GATEWAY_ID = "gateway_456"
            mock_settings.OPENAI_API_KEY = "openai_key"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = CloudflareGatewayProvider(provider_metadata)
            result = provider.get_openai_model(
                "@cf/meta/llama-3.1-8b-instruct"
            )

            expected_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {mock_settings.OPENAI_API_KEY}",
                "cf-aig-authorization": (
                    f"Bearer {mock_settings.CLOUDFLARE_API_TOKEN}"
                ),
                "cf-aig-metadata": '{"user": "test_user"}',
            }

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url=f"{provider.base_url}/openai",
                default_headers=expected_headers,
                model="@cf/meta/llama-3.1-8b-instruct",
                streaming=True,
            )
            assert result == mock_model

    def test_get_embeddings_model(self, provider_metadata):
        """Test get_embeddings_model method."""
        with (
            patch("app.utils.providers.cloudflare.settings") as mock_settings,
            patch(
                "app.utils.providers.cloudflare.OpenAIEmbeddings"
            ) as mock_embeddings,
        ):

            mock_settings.CLOUDFLARE_API_TOKEN = "cloudflare_token"
            mock_settings.CLOUDFLARE_GATEWAY_URL = (
                "https://gateway.example.com/{account_id}/{gateway_id}/ai/v1"
            )
            mock_settings.CLOUDFLARE_ACCOUNT_ID = "account_123"
            mock_settings.CLOUDFLARE_GATEWAY_ID = "gateway_456"
            mock_model = Mock()
            mock_embeddings.return_value = mock_model

            provider = CloudflareGatewayProvider(provider_metadata)
            result = provider.get_embeddings_model("@cf/baai/bge-base-en-v1.5")

            mock_embeddings.assert_called_once_with(
                api_key="X",
                base_url=provider.base_url,
                model="@cf/baai/bge-base-en-v1.5",
            )
            assert result == mock_model
