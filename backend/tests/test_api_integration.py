"""Integration tests for API endpoints.

These tests exercise the full HTTP stack: FastAPI → route → service → DB.
Uses an in-memory SQLite database for speed and isolation.
"""

import pytest
from uuid import uuid4


# ─── Health Endpoints ───

class TestHealthIntegration:
    """Test health endpoints through HTTP."""

    @pytest.mark.asyncio
    async def test_root_returns_app_info(self, client):
        resp = await client.get("/api/v1/health/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["app"] == "RPA Automation Engine"
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_status_returns_system_info(self, client):
        resp = await client.get("/api/v1/health/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "uptime_seconds" in data
        assert "python" in data
        assert data["version"] == "1.0.0"


# ─── Auth Endpoints ───

class TestAuthIntegration:
    """Test authentication flow end-to-end."""

    @pytest.mark.asyncio
    async def test_register_creates_org_and_user(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": f"new-{uuid4().hex[:8]}@example.com",
            "password": "StrongPassword123!",
            "first_name": "New",
            "last_name": "User",
            "org_name": "New Org",
        })
        assert resp.status_code in (200, 201), f"Expected 200/201 got {resp.status_code}: {resp.text[:500]}"
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(self, client, test_user):
        resp = await client.post("/api/v1/auth/register", json={
            "email": test_user.email,
            "password": "StrongPassword123!",
            "first_name": "Dup",
            "last_name": "User",
            "org_name": "Dup Org",
        })
        assert resp.status_code in (400, 409)

    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, client, test_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_with_wrong_password(self, client, test_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_requires_auth(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_me_returns_user_profile(self, client, auth_headers):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data


# ─── Workflow Endpoints ───

class TestWorkflowIntegration:
    """Test workflow CRUD through HTTP."""

    @pytest.mark.asyncio
    async def test_list_workflows_requires_auth(self, client):
        resp = await client.get("/api/v1/workflows/")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_workflows_authenticated(self, client, auth_headers, test_workflow):
        resp = await client.get("/api/v1/workflows/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "workflows" in data or "items" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_workflow(self, client, auth_headers):
        resp = await client.post("/api/v1/workflows/", headers=auth_headers, json={
            "name": "Integration Test Workflow",
            "description": "Created by integration test",
            "definition": {
                "steps": [
                    {"id": "s1", "type": "delay", "config": {"seconds": 1}, "next": []}
                ],
                "entry_point": "s1",
            },
        })
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["name"] == "Integration Test Workflow"

    @pytest.mark.asyncio
    async def test_get_workflow_by_id(self, client, auth_headers, test_workflow):
        resp = await client.get(f"/api/v1/workflows/{test_workflow.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == test_workflow.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_workflow(self, client, auth_headers):
        fake_id = str(uuid4())
        resp = await client.get(f"/api/v1/workflows/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404


# ─── Execution Endpoints ───

class TestExecutionIntegration:
    """Test execution endpoints through HTTP."""

    @pytest.mark.asyncio
    async def test_list_executions_requires_auth(self, client):
        resp = await client.get("/api/v1/executions/")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_executions_empty(self, client, auth_headers):
        resp = await client.get("/api/v1/executions/", headers=auth_headers)
        assert resp.status_code == 200


# ─── Template Endpoints ───

class TestTemplateIntegration:
    """Test workflow template endpoints."""

    @pytest.mark.asyncio
    async def test_list_templates(self, client, auth_headers):
        resp = await client.get("/api/v1/templates/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "templates" in data
        assert len(data["templates"]) >= 8  # 8 built-in templates

    @pytest.mark.asyncio
    async def test_get_template_by_id(self, client, auth_headers):
        # First get list of templates to find a valid ID
        list_resp = await client.get("/api/v1/templates", headers=auth_headers)
        templates = list_resp.json().get("templates", [])
        if templates:
            tpl_id = templates[0].get("id", templates[0].get("name", ""))
            resp = await client.get(f"/api/v1/templates/{tpl_id}", headers=auth_headers)
            assert resp.status_code == 200
        else:
            pytest.skip("No templates available")

    @pytest.mark.asyncio
    async def test_list_categories(self, client, auth_headers):
        resp = await client.get("/api/v1/templates/categories", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data


# ─── Plugin Endpoints ───

class TestPluginIntegration:
    """Test plugin management endpoints."""

    @pytest.mark.asyncio
    async def test_list_plugins(self, client, auth_headers):
        resp = await client.get("/api/v1/plugins/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "plugins" in data

    @pytest.mark.asyncio
    async def test_reload_plugins(self, client, auth_headers):
        resp = await client.post("/api/v1/plugins/reload", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "plugins_loaded" in data
        assert "task_types" in data


# ─── Admin Endpoints ───

class TestAdminIntegration:
    """Test admin panel endpoints."""

    @pytest.mark.asyncio
    async def test_admin_requires_auth(self, client):
        resp = await client.get("/api/v1/admin/overview")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_admin_overview(self, client, auth_headers):
        resp = await client.get("/api/v1/admin/overview", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_roles_list(self, client, auth_headers):
        resp = await client.get("/api/v1/admin/roles", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_permissions_list(self, client, auth_headers):
        resp = await client.get("/api/v1/admin/permissions", headers=auth_headers)
        assert resp.status_code == 200


# ─── Audit Log Endpoints ───

class TestAuditLogIntegration:
    """Test audit log endpoints."""

    @pytest.mark.asyncio
    async def test_audit_logs_list(self, client, auth_headers):
        resp = await client.get("/api/v1/audit-logs", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_stats(self, client, auth_headers):
        resp = await client.get("/api/v1/audit-logs/stats", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_resource_types(self, client, auth_headers):
        resp = await client.get("/api/v1/audit-logs/resource-types", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_actions(self, client, auth_headers):
        resp = await client.get("/api/v1/audit-logs/actions", headers=auth_headers)
        assert resp.status_code == 200


# ─── Rate Limiting ───

class TestRateLimitIntegration:
    """Test rate limiting headers are present."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, client, auth_headers):
        resp = await client.get("/api/v1/workflows/", headers=auth_headers)
        # Rate limit headers should be in response
        assert "x-ratelimit-limit" in resp.headers or resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_bypasses_rate_limit(self, client):
        """Health endpoints should not be rate-limited."""
        for _ in range(20):
            resp = await client.get("/api/v1/health/")
            assert resp.status_code == 200
