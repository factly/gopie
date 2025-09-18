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
