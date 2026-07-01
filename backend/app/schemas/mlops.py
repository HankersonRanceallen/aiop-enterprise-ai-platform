from datetime import datetime
from pydantic import BaseModel


class EvaluateRequest(BaseModel):
    question: str
    answer: str
    retrieved_chunks: list[dict] = []
    llm_provider: str | None = None   # override provider for evaluation
    source_type: str = "rag"
    source_id: int | None = None


class EvaluationOut(BaseModel):
    id: int
    question: str
    answer: str
    llm_provider: str
    llm_model: str
    faithfulness: float
    relevance: float
    completeness: float
    composite_score: float
    reasoning: dict | None
    source_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class ModelComparisonRow(BaseModel):
    model: str
    provider: str
    total_queries: int
    avg_faithfulness: float
    avg_relevance: float
    avg_completeness: float
    avg_composite: float
    avg_latency_ms: float
    avg_cost_usd: float
    total_tokens: int


class MonitoringStats(BaseModel):
    period: str
    total_requests: int
    rag_requests: int
    agent_requests: int
    error_count: int
    avg_latency_ms: float
    total_tokens: int
    estimated_cost_usd: float
    requests_by_hour: list[dict]
    top_models: list[dict]
