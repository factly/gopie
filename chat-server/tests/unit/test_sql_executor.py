from http import HTTPStatus
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.gopie.sql_executor import execute_sql


class TestExecuteSQL:
    @pytest.mark.asyncio
    async def test_execute_sql_success(self):
        """Test successful SQL query execution."""
        # Create mock response using the same pattern as conftest.py
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"data": [{"id": 1, "name": "test"}]})
        mock_response.status = 200

        mock_session = Mock()
        mock_session.post.return_value = mock_response

        with patch("app.services.gopie.sql_executor.SingletonAiohttp") as mock_singleton:
            mock_singleton.get_aiohttp_client.return_value = mock_session

            result = await execute_sql("SELECT * FROM users")

            # The function returns result_data["data"], not the full response
            assert result == [{"id": 1, "name": "test"}]

    @pytest.mark.asyncio
    async def test_execute_sql_empty_result(self):
        """Test SQL query execution with empty results."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"data": []})
        mock_response.status = 200

        mock_session = Mock()
        mock_session.post.return_value = mock_response

        with patch("app.services.gopie.sql_executor.SingletonAiohttp") as mock_singleton:
            mock_singleton.get_aiohttp_client.return_value = mock_session

            result = await execute_sql("SELECT * FROM empty_table")

            assert result == []

    @pytest.mark.asyncio
    async def test_execute_sql_http_error_with_error_message(self):
        """Test SQL query execution with HTTP error and error message."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"error": "Table 'nonexistent' doesn't exist"})
        mock_response.status = HTTPStatus.BAD_REQUEST

        mock_session = Mock()
        mock_session.post.return_value = mock_response

        with patch("app.services.gopie.sql_executor.SingletonAiohttp") as mock_singleton:
            mock_singleton.get_aiohttp_client.return_value = mock_session

            with pytest.raises(Exception, match="Table 'nonexistent' doesn't exist"):
                await execute_sql("SELECT * FROM nonexistent")

    @pytest.mark.asyncio
    async def test_execute_sql_http_error_without_error_message(self):
        """Test SQL query execution with HTTP error but no error message."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={})
        mock_response.status = HTTPStatus.INTERNAL_SERVER_ERROR

        mock_session = Mock()
        mock_session.post.return_value = mock_response

        with patch("app.services.gopie.sql_executor.SingletonAiohttp") as mock_singleton:
            mock_singleton.get_aiohttp_client.return_value = mock_session

            with pytest.raises(Exception, match="Unknown error"):
                await execute_sql("SELECT * FROM users")

    @pytest.mark.asyncio
    async def test_execute_sql_unauthorized_error(self):
        """Test SQL query execution with unauthorized error."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"error": "Unauthorized access"})
        mock_response.status = HTTPStatus.UNAUTHORIZED

        mock_session = Mock()
        mock_session.post.return_value = mock_response

        with patch("app.services.gopie.sql_executor.SingletonAiohttp") as mock_singleton:
            mock_singleton.get_aiohttp_client.return_value = mock_session

            with pytest.raises(Exception, match="Unauthorized access"):
                await execute_sql("SELECT * FROM sensitive_table")

    @pytest.mark.asyncio
    async def test_execute_sql_null_data(self):
        """Test SQL query execution with null data field."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"data": None})
        mock_response.status = 200

        mock_session = Mock()
        mock_session.post.return_value = mock_response

        with patch("app.services.gopie.sql_executor.SingletonAiohttp") as mock_singleton:
            mock_singleton.get_aiohttp_client.return_value = mock_session

            result = await execute_sql("SELECT COUNT(*) FROM users WHERE false")

            assert result is None
