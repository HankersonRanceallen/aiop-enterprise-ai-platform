"""Unit tests for app/services/rag/pipeline.py"""
import pytest
from unittest.mock import patch, AsyncMock

from app.services.rag.pipeline import _build_context, run_rag_query


class TestBuildContext:
    def test_formats_single_chunk(self):
        chunks = [{
            "document_title": "Policy.pdf",
            "chunk_index": 0,
            "content": "Employees get 20 days leave.",
        }]
        ctx = _build_context(chunks)
        assert "Policy.pdf" in ctx
        assert "20 days leave" in ctx
        assert "[1]" in ctx

    def test_formats_multiple_chunks_with_separator(self):
        chunks = [
            {"document_title": "Doc A", "chunk_index": 0, "content": "Content A"},
            {"document_title": "Doc B", "chunk_index": 1, "content": "Content B"},
        ]
        ctx = _build_context(chunks)
        assert "[1]" in ctx
        assert "[2]" in ctx
        assert "---" in ctx

    def test_empty_chunks_returns_empty_string(self):
        assert _build_context([]) == ""


class TestRunRAGQuery:
    @pytest.mark.asyncio
    async def test_returns_answer_when_chunks_found(
        self, mock_llm, mock_db, sample_chunks
    ):
        with patch(
            "app.services.rag.pipeline.retrieve_chunks",
            new=AsyncMock(return_value=sample_chunks),
        ), patch("app.services.rag.pipeline.log_rag_query"):
            result = await run_rag_query(
                db=mock_db,
                llm=mock_llm,
                question="How many days of leave do employees get?",
                organization_id=1,
            )

        assert result["answer"] == "This is a test answer."
        assert result["llm_provider"] == "mock"
        assert result["llm_model"] == "mock-model"
        assert len(result["sources"]) == 3
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50

    @pytest.mark.asyncio
    async def test_returns_not_found_when_no_chunks(self, mock_llm, mock_db):
        with patch(
            "app.services.rag.pipeline.retrieve_chunks",
            new=AsyncMock(return_value=[]),
        ):
            result = await run_rag_query(
                db=mock_db,
                llm=mock_llm,
                question="Something with no matching docs",
                organization_id=1,
            )

        assert "couldn't find" in result["answer"].lower()
        assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_includes_conversation_history(
        self, mock_llm, mock_db, sample_chunks
    ):
        history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
        ]
        with patch(
            "app.services.rag.pipeline.retrieve_chunks",
            new=AsyncMock(return_value=sample_chunks),
        ), patch("app.services.rag.pipeline.log_rag_query"):
            result = await run_rag_query(
                db=mock_db,
                llm=mock_llm,
                question="Follow-up question",
                organization_id=1,
                conversation_history=history,
            )

        assert result["answer"] is not None

    @pytest.mark.asyncio
    async def test_mlflow_logging_called(self, mock_llm, mock_db, sample_chunks):
        with patch(
            "app.services.rag.pipeline.retrieve_chunks",
            new=AsyncMock(return_value=sample_chunks),
        ), patch("app.services.rag.pipeline.log_rag_query") as mock_log:
            await run_rag_query(
                db=mock_db,
                llm=mock_llm,
                question="Test question",
                organization_id=1,
            )
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args.kwargs
            assert call_kwargs["llm_provider"] == "mock"
            assert call_kwargs["organization_id"] == 1
