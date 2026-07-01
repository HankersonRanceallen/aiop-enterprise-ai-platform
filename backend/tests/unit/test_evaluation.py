"""Unit tests for app/services/evaluation.py"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.evaluation import (
    _format_context,
    _score,
    evaluate_rag_response,
)
from app.services.llm.base import LLMResponse


class TestFormatContext:
    def test_formats_chunks_with_source_labels(self, sample_chunks):
        ctx = _format_context(sample_chunks)
        assert "[1]" in ctx
        assert "[2]" in ctx
        assert "Company Policy 2024.pdf" in ctx

    def test_limits_to_five_chunks(self):
        chunks = [
            {"content": f"Chunk {i}", "document_title": f"Doc {i}"}
            for i in range(10)
        ]
        ctx = _format_context(chunks)
        assert "[5]" in ctx
        assert "[6]" not in ctx

    def test_empty_list_returns_empty_string(self):
        assert _format_context([]) == ""


class TestScore:
    @pytest.mark.asyncio
    async def test_parses_valid_json_score(self, mock_eval_llm):
        score, reason = await _score(mock_eval_llm, "evaluate this")
        assert 0.0 <= score <= 1.0
        assert isinstance(reason, str)
        assert len(reason) > 0

    @pytest.mark.asyncio
    async def test_clamps_score_to_0_1(self):
        """Score should never go outside [0, 1] even if LLM hallucinates."""
        from tests.conftest import MockLLMService
        llm = MockLLMService(answer='{"score": 1.5, "reason": "too high"}')
        score, _ = await _score(llm, "prompt")
        assert score <= 1.0

    @pytest.mark.asyncio
    async def test_returns_fallback_on_bad_json(self):
        from tests.conftest import MockLLMService
        llm = MockLLMService(answer="not json at all")
        score, reason = await _score(llm, "prompt")
        assert score == 0.5  # neutral fallback
        assert reason == "Could not evaluate"


class TestEvaluateRAGResponse:
    @pytest.mark.asyncio
    async def test_returns_all_three_metrics(self, mock_eval_llm, sample_chunks):
        result = await evaluate_rag_response(
            llm=mock_eval_llm,
            question="How many leave days?",
            answer="Employees get 20 days of annual leave.",
            retrieved_chunks=sample_chunks,
        )
        assert 0.0 <= result.faithfulness <= 1.0
        assert 0.0 <= result.relevance <= 1.0
        assert 0.0 <= result.completeness <= 1.0

    @pytest.mark.asyncio
    async def test_composite_is_average_of_three(self, mock_eval_llm, sample_chunks):
        result = await evaluate_rag_response(
            llm=mock_eval_llm,
            question="Question",
            answer="Answer",
            retrieved_chunks=sample_chunks,
        )
        expected = (result.faithfulness + result.relevance + result.completeness) / 3
        assert result.composite == pytest.approx(expected, rel=1e-3)

    @pytest.mark.asyncio
    async def test_reasoning_has_three_keys(self, mock_eval_llm, sample_chunks):
        result = await evaluate_rag_response(
            llm=mock_eval_llm,
            question="Question",
            answer="Answer",
            retrieved_chunks=sample_chunks,
        )
        assert "faithfulness" in result.reasoning
        assert "relevance" in result.reasoning
        assert "completeness" in result.reasoning

    @pytest.mark.asyncio
    async def test_handles_empty_chunks(self, mock_eval_llm):
        result = await evaluate_rag_response(
            llm=mock_eval_llm,
            question="Question",
            answer="Answer",
            retrieved_chunks=[],
        )
        assert result.composite >= 0.0
