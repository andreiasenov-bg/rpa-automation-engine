"""Tests for health check endpoints."""

import pytest


@pytest.mark.unit
class TestHealth:
    """Health endpoint tests."""

    async def test_health_v1(self, client):
        """GET /api/v1/health returns 200 with status info."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "ok")
        assert "version" in data

    async def test_health_root(self, client):
        """GET /api/health returns 200 (unversioned — for LB probes)."""
        resp = await client.get("/api/health")
        assert resp.status_code == 200

    async def test_response_has_request_id(self, client):
        """Every response should have X-Request-ID header."""
        resp = await client.get("/api/v1/health")
        assert "x-request-id" in resp.headers

    async def test_custom_request_id_propagated(self, client):
        """If client sends X-Request-ID, it should be echoed back."""
        custom_id = "test-request-12345"
        resp = await client.get(
            "/api/v1/health",
            headers={"X-Request-ID": custom_id},
        )
        assert resp.headers.get("x-request-id") == custom_id
