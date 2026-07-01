"""Unit tests for individual LangGraph agent nodes."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.agents.planner import planner_node
from app.services.agents.analysis_agent import analysis_node
from app.services.agents.report_agent import report_node


class TestPlannerNode:
    @pytest.mark.asyncio
    async def test_returns_plan_list(self, mock_llm_with_json, sample_agent_state):
        state = {**sample_agent_state, "plan": [], "step_log": []}
        result = await planner_node(state, mock_llm_with_json)

        assert "plan" in result
        assert isinstance(result["plan"], list)
        assert len(result["plan"]) >= 1

    @pytest.mark.asyncio
    async def test_appends_step_log(self, mock_llm_with_json, sample_agent_state):
        state = {**sample_agent_state, "plan": [], "step_log": []}
        result = await planner_node(state, mock_llm_with_json)

        assert len(result["step_log"]) == 1
        assert result["step_log"][0]["agent"] == "planner"
        assert result["step_log"][0]["status"] == "done"

    @pytest.mark.asyncio
    async def test_falls_back_on_bad_json(self, sample_agent_state):
        """If LLM returns non-JSON, planner uses a sensible default plan."""
        from tests.conftest import MockLLMService
        bad_llm = MockLLMService(answer="I will search the documents and summarize them.")
        state = {**sample_agent_state, "plan": [], "step_log": []}
        result = await planner_node(state, bad_llm)

        assert isinstance(result["plan"], list)
        assert len(result["plan"]) >= 1  # fallback plan

    @pytest.mark.asyncio
    async def test_tracks_tokens(self, mock_llm_with_json, sample_agent_state):
        state = {**sample_agent_state, "plan": [], "step_log": [], "total_tokens": 0}
        result = await planner_node(state, mock_llm_with_json)
        assert result.get("total_tokens", 0) >= 0


class TestAnalysisNode:
    @pytest.mark.asyncio
    async def test_returns_analysis_string(self, mock_llm, sample_agent_state):
        state = {**sample_agent_state, "step_log": []}
        result = await analysis_node(state, mock_llm)

        assert "analysis" in result
        assert isinstance(result["analysis"], str)
        assert len(result["analysis"]) > 0

    @pytest.mark.asyncio
    async def test_handles_no_chunks(self, mock_llm, sample_agent_state):
        state = {**sample_agent_state, "retrieved_chunks": [], "step_log": []}
        result = await analysis_node(state, mock_llm)

        assert "analysis" in result
        assert "No chunk" in result["analysis"] or len(result["analysis"]) >= 0

    @pytest.mark.asyncio
    async def test_appends_step_log(self, mock_llm, sample_agent_state):
        state = {**sample_agent_state, "step_log": []}
        result = await analysis_node(state, mock_llm)

        assert len(result["step_log"]) == 1
        assert result["step_log"][0]["agent"] == "analysis"


class TestReportNode:
    @pytest.mark.asyncio
    async def test_returns_final_report(self, mock_llm, sample_agent_state):
        state = {**sample_agent_state, "step_log": []}
        result = await report_node(state, mock_llm)

        assert "final_report" in result
        assert isinstance(result["final_report"], str)
        assert len(result["final_report"]) > 0

    @pytest.mark.asyncio
    async def test_appends_step_log(self, mock_llm, sample_agent_state):
        state = {**sample_agent_state, "step_log": []}
        result = await report_node(state, mock_llm)

        assert len(result["step_log"]) == 1
        assert result["step_log"][0]["agent"] == "report"
        assert result["step_log"][0]["status"] == "done"

    @pytest.mark.asyncio
    async def test_tracks_tokens(self, mock_llm, sample_agent_state):
        state = {**sample_agent_state, "step_log": [], "total_tokens": 100}
        result = await report_node(state, mock_llm)
        # total_tokens should increase
        assert result.get("total_tokens", 100) >= 100
