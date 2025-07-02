from unittest.mock import Mock, patch

from app.utils.llm_providers.cloudflare import CloudflareLLMProvider
from app.utils.llm_providers.custom import CustomLLMProvider
from app.utils.llm_providers.litellm import LiteLLMProvider
from app.utils.llm_providers.openrouter import OpenRouterLLMProvider
from app.utils.llm_providers.portkey import PortkeyLLMProvider
from app.utils.llm_providers.portkey_self_hosted import (
    PortkeySelfHostedLLMProvider,
)


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
        with (
            patch("app.utils.llm_providers.portkey.settings") as mock_settings,
            patch(
                "app.utils.llm_providers.portkey.createHeaders"
            ) as mock_create_headers,
        ):

            mock_settings.PORTKEY_API_KEY = "test_api_key"
            mock_create_headers.return_value = {"Authorization": "Bearer test"}

            provider = PortkeyLLMProvider(sample_metadata.copy())
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

    def test_get_openai_model(self, sample_metadata):
        with (
            patch("app.utils.llm_providers.portkey.settings") as mock_settings,
            patch(
                "app.utils.llm_providers.portkey.ChatOpenAI"
            ) as mock_chat_openai,
            patch(
                "app.utils.llm_providers.portkey.createHeaders"
            ) as mock_create_headers,
            patch(
                "app.utils.llm_providers.portkey.PORTKEY_GATEWAY_URL",
                "https://api.portkey.ai",
            ),
        ):

            mock_settings.PORTKEY_API_KEY = "test_key"
            mock_settings.OPENAI_VIRTUAL_KEY = "openai_vkey"
            mock_create_headers.return_value = {"test": "headers"}
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = PortkeyLLMProvider(sample_metadata.copy())
            result = provider.get_openai_model("gpt-4")

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url="https://api.portkey.ai",
                default_headers={"test": "headers"},
                model="gpt-4",
                streaming=True,
            )
            assert result == mock_model

    def test_get_gemini_model(self, sample_metadata):
        with (
            patch("app.utils.llm_providers.portkey.settings") as mock_settings,
            patch(
                "app.utils.llm_providers.portkey.ChatOpenAI"
            ) as mock_chat_openai,
            patch(
                "app.utils.llm_providers.portkey.createHeaders"
            ) as mock_create_headers,
            patch(
                "app.utils.llm_providers.portkey.PORTKEY_GATEWAY_URL",
                "https://api.portkey.ai",
            ),
        ):

            mock_settings.PORTKEY_API_KEY = "test_key"
            mock_settings.GEMINI_VIRTUAL_KEY = "gemini_vkey"
            mock_create_headers.return_value = {"test": "headers"}
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = PortkeyLLMProvider(sample_metadata.copy())
            result = provider.get_gemini_model("gemini-pro", streaming=False)

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url="https://api.portkey.ai",
                default_headers={"test": "headers"},
                model="gemini-pro",
                streaming=False,
            )
            assert result == mock_model


class TestPortkeySelfHostedLLMProvider:
    def test_portkey_self_hosted_provider_initialization(
        self, sample_metadata
    ):
        provider = PortkeySelfHostedLLMProvider(sample_metadata)

        assert provider.user == "test_user"
        assert provider.trace_id == "test_trace_123"
        assert provider.chat_id == "test_chat_456"
        assert "test_user" in provider.headers["x-portkey-metadata"]


class TestLiteLLMProvider:
    def test_litellm_provider_initialization(self, sample_metadata):
        with patch(
            "app.utils.llm_providers.litellm.settings"
        ) as mock_settings:
            mock_settings.LITELLM_MASTER_KEY = "master_key_123"

            provider = LiteLLMProvider(sample_metadata)

            assert provider.metadata == sample_metadata
            assert provider.headers == {
                "Authorization": "Bearer master_key_123"
            }

    def test_get_openai_model(self, sample_metadata):
        with (
            patch("app.utils.llm_providers.litellm.settings") as mock_settings,
            patch(
                "app.utils.llm_providers.litellm.ChatOpenAI"
            ) as mock_chat_openai,
        ):

            mock_settings.LITELLM_MASTER_KEY = "master_key"
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = LiteLLMProvider(sample_metadata)
            result = provider.get_openai_model("gpt-4")

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url="http://localhost:4000",
                model="gpt-4",
                default_headers={"Authorization": "Bearer master_key"},
                streaming=True,
                extra_body={"metadata": sample_metadata},
            )
            assert result == mock_model

    def test_get_gemini_model(self, sample_metadata):
        with (
            patch("app.utils.llm_providers.litellm.settings") as mock_settings,
            patch(
                "app.utils.llm_providers.litellm.ChatOpenAI"
            ) as mock_chat_openai,
        ):

            mock_settings.LITELLM_MASTER_KEY = "master_key"
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = LiteLLMProvider(sample_metadata)
            result = provider.get_gemini_model("gemini-pro", streaming=False)

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
        provider = OpenRouterLLMProvider(sample_metadata)

        assert provider.metadata == sample_metadata

    def test_get_openai_model(self, sample_metadata):
        with (
            patch(
                "app.utils.llm_providers.openrouter.settings"
            ) as mock_settings,
            patch(
                "app.utils.llm_providers.openrouter.ChatOpenAI"
            ) as mock_chat_openai,
        ):

            mock_settings.OPENROUTER_API_KEY = "openrouter_key"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = OpenRouterLLMProvider(sample_metadata)
            result = provider.get_openai_model("gpt-4")

            mock_chat_openai.assert_called_once_with(
                api_key="openrouter_key",
                base_url=mock_settings.OPENROUTER_BASE_URL,
                model="openai/gpt-4",
                metadata=sample_metadata,
            )
            assert result == mock_model

    def test_get_gemini_model(self, sample_metadata):
        with (
            patch(
                "app.utils.llm_providers.openrouter.settings"
            ) as mock_settings,
            patch(
                "app.utils.llm_providers.openrouter.ChatOpenAI"
            ) as mock_chat_openai,
        ):

            mock_settings.OPENROUTER_API_KEY = "openrouter_key"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = OpenRouterLLMProvider(sample_metadata)
            result = provider.get_gemini_model("gemini-pro")

            mock_chat_openai.assert_called_once_with(
                api_key="openrouter_key",
                base_url=mock_settings.OPENROUTER_BASE_URL,
                model="google/gemini-pro",
                metadata=sample_metadata,
            )
            assert result == mock_model


class TestCloudflareLLMProvider:
    def test_cloudflare_provider_initialization(self, sample_metadata):
        provider = CloudflareLLMProvider(sample_metadata)

        assert provider.metadata == sample_metadata

    def test_get_openai_model(self, sample_metadata):
        with (
            patch(
                "app.utils.llm_providers.cloudflare.settings"
            ) as mock_settings,
            patch(
                "app.utils.llm_providers.cloudflare.ChatOpenAI"
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

            provider = CloudflareLLMProvider(sample_metadata)
            result = provider.get_openai_model(
                "@cf/meta/llama-3.1-8b-instruct"
            )

            expected_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {mock_settings.OPENAI_API_KEY}",
                "cf-aig-authorization": (
                    f"Bearer {mock_settings.CLOUDFLARE_API_TOKEN}"
                ),
                "cf-aig-metadata": '{"user": "test_user", "trace_id": "test_trace_123", "chat_id": "test_chat_456"}',
            }

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url=f"{provider.base_url}/openai",
                default_headers=expected_headers,
                model="@cf/meta/llama-3.1-8b-instruct",
                streaming=True,
            )
            assert result == mock_model

    def test_get_gemini_model(self, sample_metadata):
        with (
            patch(
                "app.utils.llm_providers.cloudflare.settings"
            ) as mock_settings,
            patch(
                "app.utils.llm_providers.cloudflare.ChatOpenAI"
            ) as mock_chat_openai,
        ):

            mock_settings.CLOUDFLARE_API_TOKEN = "cloudflare_token"
            mock_settings.CLOUDFLARE_GATEWAY_URL = (
                "https://gateway.example.com/{account_id}/{gateway_id}/ai/v1"
            )
            mock_settings.CLOUDFLARE_ACCOUNT_ID = "account_123"
            mock_settings.CLOUDFLARE_GATEWAY_ID = "gateway_456"
            mock_settings.GOOGLE_API_KEY = "google_key"
            mock_model = Mock()
            mock_chat_openai.return_value = mock_model

            provider = CloudflareLLMProvider(sample_metadata)
            result = provider.get_gemini_model("gemini-pro")

            expected_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {mock_settings.GOOGLE_API_KEY}",
                "cf-aig-authorization": (
                    f"Bearer {mock_settings.CLOUDFLARE_API_TOKEN}"
                ),
                "cf-aig-metadata": '{"user": "test_user", "trace_id": "test_trace_123", "chat_id": "test_chat_456"}',
            }

            mock_chat_openai.assert_called_once_with(
                api_key="X",
                base_url=f"{provider.base_url}/compat",
                default_headers=expected_headers,
                model="google-ai-studio/gemini-pro",
                streaming=True,
            )
            assert result == mock_model


class TestCustomLLMProvider:
    def test_custom_provider_initialization(self, sample_metadata):
        provider = CustomLLMProvider(sample_metadata)

        assert provider.metadata == sample_metadata

    def test_get_openai_model(self, sample_metadata):
        with patch("app.utils.llm_providers.custom.settings") as mock_settings:
            mock_settings.CUSTOM_LLM_API_KEY = "custom_key"
            mock_settings.CUSTOM_LLM_BASE_URL = "https://custom.api"

            provider = CustomLLMProvider(sample_metadata)

            with patch(
                "app.utils.llm_providers.custom.ChatOpenAI"
            ) as mock_chat_openai:
                mock_model = Mock()
                mock_chat_openai.return_value = mock_model

                result = provider.get_openai_model("gpt-4")

                mock_chat_openai.assert_called_once_with(
                    api_key="custom_key",
                    base_url="https://custom.api",
                    model="gpt-4",
                    metadata=sample_metadata,
                )
                assert result == mock_model

    def test_get_gemini_model(self, sample_metadata):
        with patch("app.utils.llm_providers.custom.settings") as mock_settings:
            mock_settings.CUSTOM_LLM_API_KEY = "custom_key"
            mock_settings.CUSTOM_LLM_BASE_URL = "https://custom.api"

            provider = CustomLLMProvider(sample_metadata)

            with patch(
                "app.utils.llm_providers.custom.ChatOpenAI"
            ) as mock_chat_openai:
                mock_model = Mock()
                mock_chat_openai.return_value = mock_model

                result = provider.get_gemini_model("gemini-pro")

                mock_chat_openai.assert_called_once_with(
                    api_key="custom_key",
                    base_url="https://custom.api",
                    model="gemini-pro",
                    metadata=sample_metadata,
                )
                assert result == mock_model
