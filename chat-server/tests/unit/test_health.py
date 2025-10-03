from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routers.health import router as health_router


class TestHealthEndpoints:
    @pytest.fixture
    def app(self):
        """
        Creates a FastAPI test application with the health router for testing.

        Returns:
            FastAPI: Test application instance with health endpoints.
        """
        app = FastAPI()
        app.include_router(health_router, prefix="/api/v1")
        return app

    @pytest.fixture
    def client(self, app):
        """
        Creates a test client for the FastAPI application.

        Args:
            app: FastAPI application instance.

        Returns:
            TestClient: Test client for making HTTP requests.
        """
        return TestClient(app)

    def test_health_check_success(self, client):
        """
        Test that the health check endpoint returns a successful response with correct structure.
        """
        # Mock all health check functions to return healthy status
        with (
            patch("app.api.v1.routers.health.check_qdrant_health") as mock_qdrant,
            patch("app.api.v1.routers.health.check_llm_provider_health") as mock_llm,
            patch("app.api.v1.routers.health.check_gopie_server_health") as mock_gopie,
            patch("app.api.v1.routers.health.check_embedding_provider_health") as mock_embedding,
        ):
            # Configure all health checks to return healthy status
            mock_qdrant.return_value = {"status": "healthy", "collections_count": 1}
            mock_llm.return_value = {"status": "healthy", "provider_type": "test"}
            mock_gopie.return_value = {"status": "healthy", "server_reachable": True}
            mock_embedding.return_value = {"status": "healthy", "provider_type": "test"}

            response = client.get("/api/v1/health")

            assert response.status_code == 200

            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "service" in data

            assert data["status"] == "healthy"
            assert data["service"] == "gopie-chat-server"

            # Verify timestamp is a valid ISO format
            timestamp = data["timestamp"]
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
