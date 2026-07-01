from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # What was evaluated
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    context_chunks: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # LLM used for both generation and evaluation
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)

    # Scores (0.0–1.0)
    faithfulness: Mapped[float] = mapped_column(Float, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, nullable=False)
    completeness: Mapped[float] = mapped_column(Float, nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)

    # LLM judge reasoning per metric
    reasoning: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Source (was this from a RAG query or an agent run?)
    source_type: Mapped[str] = mapped_column(String(20), default="rag")  # rag | agent
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
