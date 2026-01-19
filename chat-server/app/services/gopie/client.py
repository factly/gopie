"""
Unified client for all Gopie API requests.
Handles authentication, headers, and request management.
"""
from typing import Any, Optional

import aiohttp

from app.core.config import settings
from app.core.log import custom_logger as logger
from app.core.session import SingletonAiohttp


class GopieClient:
    """
    Unified client for making requests to the Gopie API.
    Automatically handles org-id header and base URL configuration.
    """

    def __init__(self, org_id: Optional[str] = None):
        """
        Initialize the Gopie client.

        Args:
            org_id: Organization ID to include in request headers
        """
        self.base_url = settings.GOPIE_API_ENDPOINT.rstrip("/")
        self.org_id = org_id
        self._session = SingletonAiohttp.get_aiohttp_client()

    def _get_headers(self, additional_headers: Optional[dict[str, str]] = None) -> dict[str, str]:
        """
        Build headers for the request, including org-id if available.

        Args:
            additional_headers: Optional additional headers to include

        Returns:
            Dictionary of headers
        """
        headers = {"accept": "application/json"}

        if self.org_id:
            headers["X-Organization-id"] = self.org_id

        if additional_headers:
            headers.update(additional_headers)

        return headers

    async def get(
        self,
        path: str,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """
        Make a GET request to the Gopie API.

        Args:
            path: API path (will be appended to base_url)
            headers: Optional additional headers
            **kwargs: Additional arguments to pass to aiohttp

        Returns:
            aiohttp ClientResponse
        """
        url = f"{self.base_url}{path}"
        request_headers = self._get_headers(headers)

        logger.debug(f"GET request to {url}")
        return await self._session.get(url, headers=request_headers, **kwargs)

    async def post(
        self,
        path: str,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """
        Make a POST request to the Gopie API.

        Args:
            path: API path (will be appended to base_url)
            json: JSON payload for the request
            headers: Optional additional headers
            **kwargs: Additional arguments to pass to aiohttp

        Returns:
            aiohttp ClientResponse
        """
        url = f"{self.base_url}{path}"
        request_headers = self._get_headers(headers)

        logger.debug(f"POST request to {url}")
        return await self._session.post(url, json=json, headers=request_headers, **kwargs)
