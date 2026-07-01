from datetime import datetime
from pydantic import BaseModel


class AgentRunRequest(BaseModel):
    task: str
    document_ids: list[int] | None = None  # None = search all org docs


class StepUpdate(BaseModel):
    type: str        # "step_start" | "step_done" | "complete" | "error"
    agent: str       # "planner" | "retriever" | "analysis" | "report"
    status: str      # "running" | "done" | "failed"
    message: str
    output: str | None = None
    timestamp: float | None = None


class AgentRunOut(BaseModel):
    id: int
    task: str
    status: str
    plan: list | None
    step_log: list | None
    final_report: str | None
    error: str | None
    total_tokens: int | None
    latency_ms: float | None
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class AgentRunListOut(BaseModel):
    id: int
    task: str
    status: str
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True
