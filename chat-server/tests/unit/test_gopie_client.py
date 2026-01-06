from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.gopie.client import GopieClient


class TestGopieClient:
    """Test suite for GopieClient class."""

    @pytest.mark.asyncio
    async def test_client_initialization_without_org_id(self):
        """Test GopieClient initialization without org_id."""
        with patch("app.services.gopie.client.SingletonAiohttp") as mock_singleton, patch(
            "app.services.gopie.client.settings"
        ) as mock_settings:
            mock_settings.GOPIE_API_ENDPOINT = "http://localhost:8000"
            mock_session = Mock()
            mock_singleton.get_aiohttp_client.return_value = mock_session

            client = GopieClient()

            assert client.org_id is None
            assert client.base_url == "http://localhost:8000"
            assert client._session == mock_session

    @pytest.mark.asyncio
    async def test_client_initialization_with_org_id(self):
        """Test GopieClient initialization with org_id."""
        with patch("app.services.gopie.client.SingletonAiohttp") as mock_singleton:
            mock_session = Mock()
            mock_singleton.get_aiohttp_client.return_value = mock_session

            client = GopieClient(org_id="test_org_123")

            assert client.org_id == "test_org_123"
            assert client._session == mock_session

    def test_get_headers_without_org_id(self):
        """Test _get_headers method without org_id."""
        with patch("app.services.gopie.client.SingletonAiohttp"):
            client = GopieClient()
            headers = client._get_headers()

            assert headers == {"accept": "application/json"}

    def test_get_headers_with_org_id(self):
        """Test _get_headers method with org_id."""
        with patch("app.services.gopie.client.SingletonAiohttp"):
            client = GopieClient(org_id="test_org_123")
            headers = client._get_headers()

            assert headers == {"accept": "application/json", "X-Organization-id": "test_org_123"}

    def test_get_headers_with_additional_headers(self):
        """Test _get_headers method with additional headers."""
        with patch("app.services.gopie.client.SingletonAiohttp"):
            client = GopieClient(org_id="test_org_123")
            additional = {"Authorization": "Bearer token123"}
            headers = client._get_headers(additional_headers=additional)

            assert headers == {
                "accept": "application/json",
                "X-Organization-id": "test_org_123",
                "Authorization": "Bearer token123",
            }

    @pytest.mark.asyncio
    async def test_get_request(self):
        """Test GET request method."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.status = 200

        mock_session = Mock()
        mock_session.get = AsyncMock(return_value=mock_response)

        with patch("app.services.gopie.client.SingletonAiohttp") as mock_singleton:
            mock_singleton.get_aiohttp_client.return_value = mock_session

            client = GopieClient(org_id="test_org_123")
            response = await client.get("/test/path")

            # Verify the session.get was called with correct arguments
            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args
            assert "/test/path" in call_args[0][0]
            assert call_args[1]["headers"]["X-Organization-id"] == "test_org_123"

    @pytest.mark.asyncio
    async def test_post_request(self):
        """Test POST request method."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.status = 200

        mock_session = Mock()
        mock_session.post = AsyncMock(return_value=mock_response)

        with patch("app.services.gopie.client.SingletonAiohttp") as mock_singleton:
            mock_singleton.get_aiohttp_client.return_value = mock_session

            client = GopieClient(org_id="test_org_123")
            payload = {"query": "SELECT * FROM users"}
            response = await client.post("/test/path", json=payload)

            # Verify the session.post was called with correct arguments
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            assert "/test/path" in call_args[0][0]
            assert call_args[1]["json"] == payload
            assert call_args[1]["headers"]["X-Organization-id"] == "test_org_123"

    @pytest.mark.asyncio
    async def test_get_request_without_org_id(self):
        """Test GET request without org_id in headers."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = AsyncMock(return_value=mock_response)

        with patch("app.services.gopie.client.SingletonAiohttp") as mock_singleton:
            mock_singleton.get_aiohttp_client.return_value = mock_session

            client = GopieClient()
            await client.get("/test/path")

            # Verify org-id is not in headers
            call_args = mock_session.get.call_args
            assert "org-id" not in call_args[1]["headers"]
            assert call_args[1]["headers"]["accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_post_request_with_custom_headers(self):
        """Test POST request with custom headers."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.post = AsyncMock(return_value=mock_response)

        with patch("app.services.gopie.client.SingletonAiohttp") as mock_singleton:
            mock_singleton.get_aiohttp_client.return_value = mock_session

            client = GopieClient(org_id="test_org_123")
            custom_headers = {"X-Custom-Header": "custom_value"}
            await client.post("/test/path", json={}, headers=custom_headers)

            # Verify custom header is included
            call_args = mock_session.post.call_args
            assert call_args[1]["headers"]["X-Custom-Header"] == "custom_value"
            assert call_args[1]["headers"]["X-Organization-id"] == "test_org_123"
            assert call_args[1]["headers"]["accept"] == "application/json"
