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

        with patch("app.services.gopie.sql_executor.GopieClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await execute_sql("SELECT * FROM users", org_id=None, user_id="test_user")

            # The function returns result_data["data"], not the full response
            assert result == [{"id": 1, "name": "test"}]
            mock_client_class.assert_called_once_with(org_id=None, user_id="test_user")

    @pytest.mark.asyncio
    async def test_execute_sql_empty_result(self):
        """Test SQL query execution with empty results."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"data": []})
        mock_response.status = 200

        with patch("app.services.gopie.sql_executor.GopieClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await execute_sql(
                "SELECT * FROM empty_table", org_id=None, user_id="test_user"
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_execute_sql_http_error_with_error_message(self):
        """Test SQL query execution with HTTP error and error message."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"error": "Table 'nonexistent' doesn't exist"})
        mock_response.status = HTTPStatus.BAD_REQUEST

        with patch("app.services.gopie.sql_executor.GopieClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception, match="Table 'nonexistent' doesn't exist"):
                await execute_sql("SELECT * FROM nonexistent", org_id=None, user_id="test_user")

    @pytest.mark.asyncio
    async def test_execute_sql_http_error_without_error_message(self):
        """Test SQL query execution with HTTP error but no error message."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={})
        mock_response.status = HTTPStatus.INTERNAL_SERVER_ERROR

        with patch("app.services.gopie.sql_executor.GopieClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception, match="Unknown error"):
                await execute_sql("SELECT * FROM users", org_id=None, user_id="test_user")

    @pytest.mark.asyncio
    async def test_execute_sql_unauthorized_error(self):
        """Test SQL query execution with unauthorized error."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"error": "Unauthorized access"})
        mock_response.status = HTTPStatus.UNAUTHORIZED

        with patch("app.services.gopie.sql_executor.GopieClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception, match="Unauthorized access"):
                await execute_sql("SELECT * FROM sensitive_table", org_id=None, user_id="test_user")

    @pytest.mark.asyncio
    async def test_execute_sql_null_data(self):
        """Test SQL query execution with null data field."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"data": None})
        mock_response.status = 200

        with patch("app.services.gopie.sql_executor.GopieClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await execute_sql(
                "SELECT COUNT(*) FROM users WHERE false", org_id=None, user_id="test_user"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_execute_sql_with_org_id(self):
        """Test SQL query execution with org_id parameter."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.json = AsyncMock(return_value={"data": [{"id": 1, "org": "test_org"}]})
        mock_response.status = 200

        with patch("app.services.gopie.sql_executor.GopieClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await execute_sql(
                "SELECT * FROM users", org_id="test_org_123", user_id="test_user"
            )

            assert result == [{"id": 1, "org": "test_org"}]
            mock_client_class.assert_called_once_with(org_id="test_org_123", user_id="test_user")
