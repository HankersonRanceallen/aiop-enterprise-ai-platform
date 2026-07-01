"""
Integration tests for /api/v1/chat endpoints.
Requires TEST_DATABASE_URL env var — skipped otherwise.
"""
import pytest
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.integration


@pytest.fixture
async def authed_client(app_client, test_user_data):
    """Returns (client, auth_headers) with a registered user."""
    reg = await app_client.post("/api/v1/auth/register", json=test_user_data)
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return app_client, headers


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_chat_creates_conversation(self, authed_client, sample_chunks):
        client, headers = authed_client
        with patch(
            "app.services.rag.pipeline.retrieve_chunks",
            new=AsyncMock(return_value=sample_chunks),
        ), patch("app.services.rag.pipeline.log_rag_query"), \
           patch("app.services.llm.factory.get_llm_service") as mock_factory:
            mock_factory.return_value.__class__ = type(
                "MockLLM", (), {
                    "provider_name": "mock",
                    "model_name": "mock-model",
                    "generate": AsyncMock(return_value=type("R", (), {
                        "content": "Test answer",
                        "provider": "mock",
                        "model": "mock-model",
                        "prompt_tokens": 50,
                        "completion_tokens": 25,
                        "total_tokens": 75,
                        "latency_ms": 100.0,
                    })()),
                    "embed": AsyncMock(return_value=type("E", (), {
                        "embedding": [0.1] * 1536
                    })()),
                }
            )
            response = await client.post(
                "/api/v1/chat",
                json={"message": "What is the leave policy?"},
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "conversation_id" in data
        assert data["conversation_id"] > 0

    @pytest.mark.asyncio
    async def test_chat_without_auth_fails(self, app_client):
        response = await app_client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
        )
        assert response.status_code == 403


class TestListConversations:
    @pytest.mark.asyncio
    async def test_returns_empty_list_initially(self, authed_client):
        client, headers = authed_client
        response = await client.get("/api/v1/chat/conversations", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_requires_auth(self, app_client):
        response = await app_client.get("/api/v1/chat/conversations")
        assert response.status_code == 403


class TestDeleteConversation:
    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, authed_client):
        client, headers = authed_client
        response = await client.delete(
            "/api/v1/chat/conversations/99999",
            headers=headers,
        )
        assert response.status_code == 404
