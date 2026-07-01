"""Unit tests for app/services/mlflow_service.py"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.mlflow_service import calculate_cost, log_rag_query, log_agent_run


class TestCalculateCost:
    def test_gpt4o_cost(self):
        cost = calculate_cost("gpt-4o", prompt_tokens=1_000_000, completion_tokens=1_000_000)
        assert cost == pytest.approx(12.50, rel=1e-3)  # $2.50 in + $10.00 out

    def test_ollama_is_free(self):
        cost = calculate_cost("llama3.1", prompt_tokens=100_000, completion_tokens=50_000)
        assert cost == 0.0

    def test_unknown_model_defaults_to_zero(self):
        cost = calculate_cost("unknown-model-xyz", prompt_tokens=1000, completion_tokens=500)
        assert cost == 0.0

    def test_zero_tokens_gives_zero_cost(self):
        assert calculate_cost("gpt-4o", 0, 0) == 0.0

    def test_claude_sonnet_cost(self):
        # $3.00/1M input + $15.00/1M output
        cost = calculate_cost(
            "claude-3-5-sonnet-20241022",
            prompt_tokens=500_000,
            completion_tokens=500_000,
        )
        assert cost == pytest.approx(9.00, rel=1e-3)

    def test_cost_is_rounded_to_6_decimals(self):
        cost = calculate_cost("gpt-4o", 100, 50)
        assert isinstance(cost, float)
        # Should not have excessive precision
        assert len(str(cost).split(".")[-1]) <= 6


class TestMLflowLogging:
    """MLflow calls should never raise — even if MLflow is unreachable."""

    def test_log_rag_query_silent_on_error(self):
        with patch("app.services.mlflow_service.mlflow") as mock_mlflow:
            mock_mlflow.start_run.side_effect = Exception("MLflow unreachable")
            # Should NOT raise
            log_rag_query(
                question="test",
                llm_provider="openai",
                llm_model="gpt-4o",
                prompt_tokens=100,
                completion_tokens=50,
                latency_ms=200.0,
                chunks_retrieved=5,
                organization_id=1,
            )

    def test_log_agent_run_silent_on_error(self):
        with patch("app.services.mlflow_service.mlflow") as mock_mlflow:
            mock_mlflow.start_run.side_effect = ConnectionError("No MLflow")
            log_agent_run(
                task="test task",
                llm_provider="openai",
                llm_model="gpt-4o",
                total_tokens=300,
                latency_ms=1500.0,
                step_log=[],
                organization_id=1,
                succeeded=True,
            )
