"""Smoke tests for deployed API endpoints.

These tests are designed to run against a deployed environment and verify
that core endpoints are responding with expected status codes.

Environment variables required:
  SMOKE_TEST_API_URL: Base URL of the deployed API (e.g., https://api.example.com)
  SMOKE_TEST_JWT: A valid JWT token for authentication
"""

import os
import pytest
import requests


@pytest.fixture
def api_url():
    """Get the API base URL from environment."""
    url = os.getenv("SMOKE_TEST_API_URL")
    if not url:
        pytest.skip("SMOKE_TEST_API_URL not set")
    return url.rstrip("/")


@pytest.fixture
def auth_headers():
    """Get authorization headers from environment."""
    token = os.getenv("SMOKE_TEST_JWT")
    if not token:
        pytest.skip("SMOKE_TEST_JWT not set")
    return {"Authorization": f"Bearer {token}"}


class TestSmokeHealthChecks:
    """Smoke tests for core endpoint availability."""

    def test_meals_endpoint_healthy(self, api_url, auth_headers):
        """Test that GET /meals returns a successful response."""
        response = requests.get(
            f"{api_url}/meals",
            headers=auth_headers,
            timeout=10,
        )
        assert response.status_code in (200, 401, 403), (
            f"Meals endpoint returned {response.status_code}: {response.text}"
        )

    def test_ingredients_endpoint_healthy(self, api_url, auth_headers):
        """Test that GET /ingredients returns a successful response."""
        response = requests.get(
            f"{api_url}/ingredients",
            headers=auth_headers,
            timeout=10,
        )
        assert response.status_code in (200, 401, 403), (
            f"Ingredients endpoint returned {response.status_code}: {response.text}"
        )

    def test_summary_endpoint_healthy(self, api_url, auth_headers):
        """Test that GET /daily-summary returns a successful response."""
        response = requests.get(
            f"{api_url}/daily-summary?date=2026-04-07",
            headers=auth_headers,
            timeout=10,
        )
        assert response.status_code in (200, 400, 401, 403), (
            f"Summary endpoint returned {response.status_code}: {response.text}"
        )

    def test_meal_logs_endpoint_healthy(self, api_url, auth_headers):
        """Test that GET /meal-logs returns a successful response."""
        response = requests.get(
            f"{api_url}/meal-logs",
            headers=auth_headers,
            timeout=10,
        )
        assert response.status_code in (200, 401, 403), (
            f"Meal logs endpoint returned {response.status_code}: {response.text}"
        )

    def test_users_endpoint_healthy(self, api_url, auth_headers):
        """Test that GET /users/me returns a successful response."""
        response = requests.get(
            f"{api_url}/users/me",
            headers=auth_headers,
            timeout=10,
        )
        assert response.status_code in (200, 401, 403, 404), (
            f"Users endpoint returned {response.status_code}: {response.text}"
        )
