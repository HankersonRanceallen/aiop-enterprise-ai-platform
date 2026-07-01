"""
Integration tests for /api/v1/auth endpoints.
Requires TEST_DATABASE_URL env var — skipped otherwise.
"""
import pytest


pytestmark = pytest.mark.integration


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_returns_tokens(self, app_client, test_user_data):
        response = await app_client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(self, app_client, test_user_data):
        await app_client.post("/api/v1/auth/register", json=test_user_data)
        response = await app_client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_without_org(self, app_client):
        response = await app_client.post("/api/v1/auth/register", json={
            "email": "noorg@example.com",
            "full_name": "No Org User",
            "password": "password123",
        })
        assert response.status_code == 201


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, app_client, test_user_data):
        await app_client.post("/api/v1/auth/register", json=test_user_data)
        response = await app_client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_login_wrong_password_fails(self, app_client, test_user_data):
        await app_client.post("/api/v1/auth/register", json=test_user_data)
        response = await app_client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email_fails(self, app_client):
        response = await app_client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert response.status_code == 401


class TestMe:
    @pytest.mark.asyncio
    async def test_me_returns_current_user(self, app_client, test_user_data):
        reg = await app_client.post("/api/v1/auth/register", json=test_user_data)
        token = reg.json()["access_token"]
        response = await app_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["full_name"] == test_user_data["full_name"]

    @pytest.mark.asyncio
    async def test_me_without_token_fails(self, app_client):
        response = await app_client.get("/api/v1/auth/me")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_me_with_invalid_token_fails(self, app_client):
        response = await app_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not.a.real.token"},
        )
        assert response.status_code == 401
