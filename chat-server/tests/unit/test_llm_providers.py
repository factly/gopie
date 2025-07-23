from unittest.mock import Mock, patch

from portkey_ai import PORTKEY_GATEWAY_URL

from app.utils.providers.llm_providers.cloudflare import CloudflareLLMProvider
from app.utils.providers.llm_providers.custom import CustomLLMProvider
from app.utils.providers.llm_providers.litellm import LiteLLMProvider
from app.utils.providers.llm_providers.openrouter import OpenRouterLLMProvider
from app.utils.providers.llm_providers.portkey import PortkeyLLMProvider


class TestPortkeyLLMProvider:
    def test_portkey_provider_initialization(self, sample_metadata):
        provider = PortkeyLLMProvider(sample_metadata.copy())

        assert provider.user == "test_user"
        assert provider.trace_id == "test_trace_123"
        assert provider.chat_id == "test_chat_456"

    def test_portkey_provider_initialization_with_defaults(self):
        provider = PortkeyLLMProvider({})

        assert provider.user == ""
        assert provider.trace_id == ""
        assert provider.chat_id == ""
        assert provider.metadata == {}

    def test_get_headers(self, sample_metadata):
        """
        Test that PortkeyLLMProvider.get_headers returns the correct headers and calls createHeaders with expected arguments.
        """
        with (
            patch("app.utils.providers.llm_providers.portkey.settings") as mock_settings,
            patch("app.utils.providers.llm_providers.portkey.createHeaders") as mock_create_headers,
        ):

            mock_settings.PORTKEY_API_KEY = "test_api_key"
            mock_settings.PORTKEY_PROVIDER_API_KEY = None
            mock_settings.PORTKEY_PROVIDER_NAME = None
            mock_settings.PORTKEY_CONFIG_ID = None
            mock_settings.PORTKEY_URL = None
            mock_create_headers.return_value = {"Authorization": "Bearer test"}

            provider = PortkeyLLMProvider(sample_metadata.copy())
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

    def test_get_llm_model(self, sample_metadata):
        """
        Tests that `PortkeyLLMProvider.get_llm_model` initializes and returns a ChatOpenAI model with the correct parameters, including API key, base URL, headers, model name, and streaming enabled.
        """
        with (
            patch("app.utils.providers.llm_providers.portkey.settings") as mock_settings,
            patch("app.utils.providers.llm_providers.portkey.ChatOpenAI") as mock_chat_openai,
            patch("app.utils.providers.llm_providers.portkey.createHeaders") as mock_create_headers,
            patch(
                "app.utils.providers.llm_providers.portkey.PORTKEY_GATEWAY_URL",
                PORTKEY_GATEWAY_URL,
            ),
        ):

            mock_settings.PORTKEY_API_KEY = "test_key"
            mock_settings.PORTKEY_PROVIDER_API_KEY = None
            mock_settings.PORTKEY_PROVIDER_NAME = None
            mock_settings.PORTKEY_CONFIG_ID = None
            mock_settings.PORTKEY_URL = None
            mock_create_headers.return_value = {"test": "headers"}
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = PortkeyLLMProvider(sample_metadata.copy())
            result = provider.get_llm_model("gpt-4")

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url=PORTKEY_GATEWAY_URL,
                default_headers={"test": "headers"},
                model="gpt-4",
                streaming=True,
            )
            assert result == mock_model

    def test_get_llm_model_with_streaming_false(self, sample_metadata):
        """
        Test that PortkeyLLMProvider.get_llm_model returns the correct model instance with streaming disabled.

        Verifies that the ChatOpenAI class is called with the expected parameters when requesting a non-streaming model, and that the returned object matches the mocked model.
        """
        with (
            patch("app.utils.providers.llm_providers.portkey.settings") as mock_settings,
            patch("app.utils.providers.llm_providers.portkey.ChatOpenAI") as mock_chat_openai,
            patch("app.utils.providers.llm_providers.portkey.createHeaders") as mock_create_headers,
            patch(
                "app.utils.providers.llm_providers.portkey.PORTKEY_GATEWAY_URL",
                PORTKEY_GATEWAY_URL,
            ),
        ):

            mock_settings.PORTKEY_API_KEY = "test_key"
            mock_settings.PORTKEY_PROVIDER_API_KEY = None
            mock_settings.PORTKEY_PROVIDER_NAME = None
            mock_settings.PORTKEY_CONFIG_ID = None
            mock_settings.PORTKEY_URL = None
            mock_create_headers.return_value = {"test": "headers"}
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = PortkeyLLMProvider(sample_metadata.copy())
            result = provider.get_llm_model("gemini-pro", streaming=False)

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url=PORTKEY_GATEWAY_URL,
                default_headers={"test": "headers"},
                model="gemini-pro",
                streaming=False,
            )
            assert result == mock_model

    def test_self_hosted_provider_initialization(self, sample_metadata):
        """
        Test that PortkeyLLMProvider initializes correctly with self-hosted configuration and provider API key.

        Verifies that the provider's user, trace ID, chat ID, self-hosted flag, and provider API key are set as expected when self-hosted settings are provided.
        """
        with patch("app.utils.providers.llm_providers.portkey.settings") as mock_settings:
            mock_settings.PORTKEY_API_KEY = "test_key"
            mock_settings.PORTKEY_PROVIDER_API_KEY = "provider_key"
            mock_settings.PORTKEY_PROVIDER_NAME = "test_provider"
            mock_settings.PORTKEY_CONFIG_ID = None
            mock_settings.PORTKEY_URL = "https://self-hosted.portkey.ai"

            provider = PortkeyLLMProvider(sample_metadata)

            assert provider.user == "test_user"
            assert provider.trace_id == "test_trace_123"
            assert provider.chat_id == "test_chat_456"
            assert provider.self_hosted is True
            assert provider.provider_api_key == "provider_key"


class TestLiteLLMProvider:
    def test_litellm_provider_initialization(self, sample_metadata):
        """
        Tests that LiteLLMProvider initializes with the correct metadata and authorization headers using the provided settings.
        """
        with patch("app.utils.providers.llm_providers.litellm.settings") as mock_settings:
            mock_settings.LITELLM_MASTER_KEY = "master_key_123"
            mock_settings.LITELLM_KEY_HEADER_NAME = None
            mock_settings.LITELLM_VIRTUAL_KEY = None

            provider = LiteLLMProvider(sample_metadata)

            assert provider.metadata == sample_metadata
            assert provider.headers == {"Authorization": "Bearer master_key_123"}

    def test_get_llm_model(self, sample_metadata):
        """
        Tests that LiteLLMProvider.get_llm_model initializes and returns a ChatOpenAI model with the correct parameters and metadata.
        """
        with (
            patch("app.utils.providers.llm_providers.litellm.settings") as mock_settings,
            patch("app.utils.providers.llm_providers.litellm.ChatOpenAI") as mock_chat_openai,
        ):

            mock_settings.LITELLM_MASTER_KEY = "master_key"
            mock_settings.LITELLM_KEY_HEADER_NAME = None
            mock_settings.LITELLM_VIRTUAL_KEY = None
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = LiteLLMProvider(sample_metadata)
            result = provider.get_llm_model("gpt-4")

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url="http://localhost:4000",
                model="gpt-4",
                default_headers={"Authorization": "Bearer master_key"},
                streaming=True,
                extra_body={"metadata": sample_metadata},
            )
            assert result == mock_model

    def test_get_llm_model_with_streaming_false(self, sample_metadata):
        """
        Tests that LiteLLMProvider.get_llm_model returns the correct model instance with streaming disabled and passes the expected parameters to ChatOpenAI.
        """
        with (
            patch("app.utils.providers.llm_providers.litellm.settings") as mock_settings,
            patch("app.utils.providers.llm_providers.litellm.ChatOpenAI") as mock_chat_openai,
        ):

            mock_settings.LITELLM_MASTER_KEY = "master_key"
            mock_settings.LITELLM_KEY_HEADER_NAME = None
            mock_settings.LITELLM_VIRTUAL_KEY = None
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = LiteLLMProvider(sample_metadata)
            result = provider.get_llm_model("gemini-pro", streaming=False)

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url="http://localhost:4000",
                model="gemini-pro",
                default_headers={"Authorization": "Bearer master_key"},
                streaming=False,
                extra_body={"metadata": sample_metadata},
            )
            assert result == mock_model


class TestOpenRouterLLMProvider:
    def test_openrouter_provider_initialization(self, sample_metadata):
        """
        Tests that the OpenRouterLLMProvider initializes with the provided metadata.
        """
        provider = OpenRouterLLMProvider(sample_metadata)

        assert provider.metadata == sample_metadata

    def test_get_llm_model(self, sample_metadata):
        """
        Tests that `OpenRouterLLMProvider.get_llm_model` initializes a `ChatOpenAI` model with the correct API key, base URL, model name, metadata, and streaming enabled, and returns the resulting model instance.
        """
        with (
            patch("app.utils.providers.llm_providers.openrouter.settings") as mock_settings,
            patch("app.utils.providers.llm_providers.openrouter.ChatOpenAI") as mock_chat_openai,
        ):

            mock_settings.OPENROUTER_API_KEY = "openrouter_key"
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = OpenRouterLLMProvider(sample_metadata)
            result = provider.get_llm_model("gpt-4")

            mock_chat_openai.assert_called_once_with(
                api_key="openrouter_key",
                base_url="https://openrouter.ai/api/v1",
                model="gpt-4",
                metadata=sample_metadata,
                streaming=True,
            )
            assert result == mock_model

    def test_get_llm_model_with_streaming_false(self, sample_metadata):
        """
        Test that OpenRouterLLMProvider.get_llm_model returns the correct model instance with streaming disabled.

        Verifies that the ChatOpenAI class is called with the expected API key, base URL, model name, metadata, and streaming flag set to False, and that the returned model matches the mock.
        """
        with (
            patch("app.utils.providers.llm_providers.openrouter.settings") as mock_settings,
            patch("app.utils.providers.llm_providers.openrouter.ChatOpenAI") as mock_chat_openai,
        ):

            mock_settings.OPENROUTER_API_KEY = "openrouter_key"
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = OpenRouterLLMProvider(sample_metadata)
            result = provider.get_llm_model("gemini-pro", streaming=False)

            mock_chat_openai.assert_called_once_with(
                api_key="openrouter_key",
                base_url="https://openrouter.ai/api/v1",
                model="gemini-pro",
                metadata=sample_metadata,
                streaming=False,
            )
            assert result == mock_model


class TestCloudflareProvider:
    def test_cloudflare_provider_initialization(self, sample_metadata):
        """
        Tests that the CloudflareLLMProvider initializes with the provided metadata.
        """
        provider = CloudflareLLMProvider(sample_metadata)

        assert provider.metadata == sample_metadata

    def test_get_llm_model(self, sample_metadata):
        """
        Tests that CloudflareLLMProvider's get_llm_model method initializes a ChatOpenAI model with the correct base URL, headers, model name, and streaming enabled, using provided metadata.
        """
        with (
            patch("app.utils.providers.llm_providers.cloudflare.settings") as mock_settings,
            patch("app.utils.providers.llm_providers.cloudflare.ChatOpenAI") as mock_chat_openai,
        ):

            mock_settings.CLOUDFLARE_GATEWAY_URL = "https://gateway.ai.cloudflare.com"
            mock_settings.CLOUDFLARE_PROVIDER = "workers-ai"
            mock_settings.CLOUDFLARE_ACCOUNT_ID = "account_id"
            mock_settings.CLOUDFLARE_GATEWAY_ID = "gateway_id"
            mock_settings.CLOUDFLARE_PROVIDER_API_KEY = "provider_key"
            mock_settings.CLOUDFLARE_API_TOKEN = "api_token"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = CloudflareLLMProvider(sample_metadata)
            result = provider.get_llm_model("@cf/meta/llama-3.1-8b-instruct")

            expected_base_url = (
                "https://gateway.ai.cloudflare.com/workers-ai/account_id/gateway_id/compat"
            )
            expected_headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer provider_key",
                "cf-aig-authorization": "Bearer api_token",
                "cf-aig-metadata": '{"user": "test_user", "trace_id": "test_trace_123", "chat_id": "test_chat_456"}',
            }
            mock_chat_openai.assert_called_once_with(
                api_key="X",  # This is hardcoded in the actual implementation
                base_url=expected_base_url,
                model="@cf/meta/llama-3.1-8b-instruct",
                default_headers=expected_headers,
                streaming=True,
            )
            assert result == mock_model


class TestCustomLLMProvider:
    def test_custom_provider_initialization(self, sample_metadata):
        """
        Test that CustomLLMProvider initializes with the provided metadata.
        """
        provider = CustomLLMProvider(sample_metadata)

        assert provider.metadata == sample_metadata

    def test_get_llm_model(self, sample_metadata):
        """
        Test that CustomLLMProvider.get_llm_model initializes and returns a ChatOpenAI model with the correct parameters using provided metadata.
        """
        with (
            patch("app.utils.providers.llm_providers.custom.settings") as mock_settings,
            patch("app.utils.providers.llm_providers.custom.ChatOpenAI") as mock_chat_openai,
        ):

            mock_settings.CUSTOM_LLM_API_KEY = "custom_key"
            mock_settings.CUSTOM_LLM_BASE_URL = "https://custom.api"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = CustomLLMProvider(sample_metadata)
            result = provider.get_llm_model("gpt-4")

            mock_chat_openai.assert_called_once_with(
                api_key="custom_key",
                base_url="https://custom.api",
                model="gpt-4",
                metadata={
                    "user": "test_user",
                    "trace_id": "test_trace_123",
                    "chat_id": "test_chat_456",
                },
                streaming=True,
            )
            assert result == mock_model

    def test_get_llm_model_with_streaming_false(self, sample_metadata):
        """
        Test that CustomLLMProvider.get_llm_model returns the correct model instance with streaming disabled and passes the expected parameters to ChatOpenAI.
        """
        with (
            patch("app.utils.providers.llm_providers.custom.settings") as mock_settings,
            patch("app.utils.providers.llm_providers.custom.ChatOpenAI") as mock_chat_openai,
        ):

            mock_settings.CUSTOM_LLM_API_KEY = "custom_key"
            mock_settings.CUSTOM_LLM_BASE_URL = "https://custom.api"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = CustomLLMProvider(sample_metadata)
            result = provider.get_llm_model("gemini-pro", streaming=False)

            mock_chat_openai.assert_called_once_with(
                api_key="custom_key",
                base_url="https://custom.api",
                model="gemini-pro",
                metadata={
                    "user": "test_user",
                    "trace_id": "test_trace_123",
                    "chat_id": "test_chat_456",
                },
                streaming=False,
            )
            assert result == mock_model
