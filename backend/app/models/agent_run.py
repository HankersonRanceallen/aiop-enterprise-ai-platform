from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, JSON, Float, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentRunStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus), default=AgentRunStatus.PENDING
    )

    # Planner output - list of planned steps
    plan: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Step-by-step log from all agents
    step_log: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Final generated report
    final_report: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Error message if failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
