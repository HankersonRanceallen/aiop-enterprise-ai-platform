"""
conftest.py
============
Shared fixtures for all tests.

Unit tests: mock the LLM and DB — zero external dependencies.
Integration tests: require a real PostgreSQL (skip if not available).
                   Run with: pytest -m integration
"""
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.services.llm.base import BaseLLMService, LLMResponse, EmbeddingResponse


# ─── Mock LLM ────────────────────────────────────────────────────────────────

class MockLLMService(BaseLLMService):
    """Deterministic fake LLM — no API calls, instant, free."""

    def __init__(self, answer: str = "This is a test answer.", embedding_dims: int = 1536):
        self._answer = answer
        self._embedding = [0.1] * embedding_dims

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model"

    async def generate(self, messages, system_prompt=None, temperature=0.1, max_tokens=2048):
        return LLMResponse(
            content=self._answer,
            provider="mock",
            model="mock-model",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=10.0,
        )

    async def embed(self, text: str):
        return EmbeddingResponse(
            embedding=self._embedding,
            provider="mock",
            model="mock-embedding",
            tokens_used=10,
        )


@pytest.fixture
def mock_llm():
    return MockLLMService()


@pytest.fixture
def mock_llm_with_json():
    """LLM that returns valid JSON — used for planner and evaluation tests."""
    return MockLLMService(answer='["Step 1: Search documents", "Step 2: Analyze", "Step 3: Report"]')


@pytest.fixture
def mock_eval_llm():
    """LLM that returns evaluation JSON scores."""
    return MockLLMService(answer='{"score": 0.9, "reason": "Answer is well grounded in context."}')


# ─── Mock DB session ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """Async mock of SQLAlchemy AsyncSession."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.rollback = AsyncMock()
    return db


# ─── Sample data ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_chunks():
    return [
        {
            "id": 1,
            "document_id": 1,
            "document_title": "Company Policy 2024.pdf",
            "chunk_index": 0,
            "content": "Employees are entitled to 20 days of annual leave per year.",
            "score": 0.92,
        },
        {
            "id": 2,
            "document_id": 1,
            "document_title": "Company Policy 2024.pdf",
            "chunk_index": 1,
            "content": "Remote work is permitted up to 3 days per week with manager approval.",
            "score": 0.85,
        },
        {
            "id": 3,
            "document_id": 2,
            "document_title": "Employee Handbook.docx",
            "chunk_index": 4,
            "content": "Performance reviews are conducted bi-annually in June and December.",
            "score": 0.78,
        },
    ]


@pytest.fixture
def sample_agent_state(sample_chunks):
    return {
        "task": "Summarize the HR policies",
        "organization_id": 1,
        "document_ids": None,
        "plan": ["Search HR documents", "Analyze policies", "Generate summary"],
        "retrieved_chunks": sample_chunks,
        "analysis": "The company has generous leave policies and supports remote work.",
        "final_report": "",
        "step_log": [],
        "total_tokens": 0,
        "error": None,
    }


# ─── Integration test app client ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def integration_db_url():
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set — skipping integration tests")
    return url


@pytest_asyncio.fixture
async def app_client(integration_db_url, monkeypatch):
    """
    Real FastAPI test client backed by a test database.
    Requires TEST_DATABASE_URL env var.
    """
    monkeypatch.setenv("DATABASE_URL", integration_db_url)
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-testing-only")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-key")

    from app.main import app
    from app.core.database import init_db
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def test_user_data():
    return {
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "testpassword123",
        "organization_name": "Test Org",
    }
