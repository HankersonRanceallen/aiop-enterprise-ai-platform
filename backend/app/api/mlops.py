"""
MLOps API
==========
Endpoints for the V3 MLOps layer:

  POST /mlops/evaluate          Run LLM-as-judge on a Q&A pair
  GET  /mlops/evaluations       List evaluation results
  GET  /mlops/model-comparison  The model comparison table (GPT vs Claude vs Ollama)
  GET  /mlops/monitoring        Request volume, error rates, token usage
  GET  /mlops/mlflow-url        URL to the MLflow tracking UI
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.core.config import settings
from app.core.database import get_db
from app.models.evaluation import EvaluationResult
from app.models.conversation import Message, Conversation
from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.user import User
from app.schemas.mlops import (
    EvaluateRequest, EvaluationOut,
    ModelComparisonRow, MonitoringStats,
)
from app.api.deps import get_current_user
from app.services.evaluation import evaluate_rag_response
from app.services.mlflow_service import (
    log_evaluation, calculate_cost, MODEL_PRICING
)
from app.services.llm.factory import get_llm_service

router = APIRouter(prefix="/mlops", tags=["mlops"])


# ─── Evaluate ────────────────────────────────────────────────────────────────

@router.post("/evaluate", response_model=EvaluationOut, status_code=201)
async def evaluate(
    payload: EvaluateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run LLM-as-judge evaluation on a Q&A pair.
    Scores faithfulness, relevance, and completeness 0–1.
    Logs results to MLflow automatically.
    """
    llm = get_llm_service(payload.llm_provider)

    result = await evaluate_rag_response(
        llm=llm,
        question=payload.question,
        answer=payload.answer,
        retrieved_chunks=payload.retrieved_chunks,
    )

    record = EvaluationResult(
        question=payload.question,
        answer=payload.answer,
        context_chunks=payload.retrieved_chunks[:3] if payload.retrieved_chunks else None,
        llm_provider=llm.provider_name,
        llm_model=llm.model_name,
        faithfulness=result.faithfulness,
        relevance=result.relevance,
        completeness=result.completeness,
        composite_score=result.composite,
        reasoning=result.reasoning,
        source_type=payload.source_type,
        source_id=payload.source_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Log to MLflow (non-blocking)
    log_evaluation(
        question=payload.question,
        llm_model=llm.model_name,
        faithfulness=result.faithfulness,
        relevance=result.relevance,
        completeness=result.completeness,
        organization_id=current_user.organization_id,
    )

    return record


@router.get("/evaluations", response_model=list[EvaluationOut])
async def list_evaluations(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EvaluationResult)
        .where(EvaluationResult.organization_id == current_user.organization_id)
        .order_by(EvaluationResult.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ─── Model comparison ────────────────────────────────────────────────────────

@router.get("/model-comparison", response_model=list[ModelComparisonRow])
async def model_comparison(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The centrepiece of V3 — compares all LLM providers by:
    accuracy, cost, latency, and token usage.

    This is the table senior AI engineers talk about in interviews.
    """
    org_id = current_user.organization_id

    # Evaluation metrics per model
    eval_result = await db.execute(
        text("""
            SELECT
                llm_model,
                llm_provider,
                COUNT(*)              AS total_evals,
                AVG(faithfulness)     AS avg_faithfulness,
                AVG(relevance)        AS avg_relevance,
                AVG(completeness)     AS avg_completeness,
                AVG(composite_score)  AS avg_composite
            FROM evaluation_results
            WHERE organization_id = :org_id
            GROUP BY llm_model, llm_provider
        """),
        {"org_id": org_id},
    )
    eval_rows = {(r.llm_model, r.llm_provider): r for r in eval_result}

    # Latency + token metrics per model from message history
    msg_result = await db.execute(
        text("""
            SELECT
                m.llm_model,
                m.llm_provider,
                COUNT(*)                     AS total_queries,
                AVG(m.latency_ms)            AS avg_latency_ms,
                SUM(COALESCE(m.prompt_tokens, 0) + COALESCE(m.completion_tokens, 0)) AS total_tokens,
                AVG(COALESCE(m.prompt_tokens, 0))     AS avg_prompt_tokens,
                AVG(COALESCE(m.completion_tokens, 0)) AS avg_completion_tokens
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.organization_id = :org_id
              AND m.llm_model IS NOT NULL
            GROUP BY m.llm_model, m.llm_provider
        """),
        {"org_id": org_id},
    )
    msg_rows = {(r.llm_model, r.llm_provider): r for r in msg_result}

    # Merge both sources
    all_keys = set(eval_rows.keys()) | set(msg_rows.keys())
    rows = []

    for model, provider in all_keys:
        ev = eval_rows.get((model, provider))
        mg = msg_rows.get((model, provider))

        avg_prompt  = float(mg.avg_prompt_tokens or 0)     if mg else 0
        avg_compl   = float(mg.avg_completion_tokens or 0) if mg else 0
        avg_cost    = calculate_cost(model, int(avg_prompt), int(avg_compl))

        rows.append(ModelComparisonRow(
            model=model,
            provider=provider,
            total_queries=int(mg.total_queries) if mg else 0,
            avg_faithfulness=round(float(ev.avg_faithfulness), 3) if ev else 0.0,
            avg_relevance=round(float(ev.avg_relevance), 3)       if ev else 0.0,
            avg_completeness=round(float(ev.avg_completeness), 3) if ev else 0.0,
            avg_composite=round(float(ev.avg_composite), 3)       if ev else 0.0,
            avg_latency_ms=round(float(mg.avg_latency_ms or 0), 1) if mg else 0.0,
            avg_cost_usd=avg_cost,
            total_tokens=int(mg.total_tokens or 0) if mg else 0,
        ))

    return sorted(rows, key=lambda r: r.avg_composite, reverse=True)


# ─── Monitoring ──────────────────────────────────────────────────────────────

@router.get("/monitoring")
async def monitoring(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Real-time platform health: requests, errors, tokens, cost."""
    org_id = current_user.organization_id
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Total RAG messages in window
    msg_result = await db.execute(
        text("""
            SELECT
                COUNT(*)                                    AS total,
                AVG(m.latency_ms)                          AS avg_latency,
                SUM(COALESCE(m.prompt_tokens,0) + COALESCE(m.completion_tokens,0)) AS tokens,
                m.llm_model,
                m.llm_provider,
                AVG(COALESCE(m.prompt_tokens,0))           AS avg_prompt,
                AVG(COALESCE(m.completion_tokens,0))       AS avg_compl
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.organization_id = :org_id
              AND m.created_at >= :since
              AND m.llm_model IS NOT NULL
            GROUP BY m.llm_model, m.llm_provider
        """),
        {"org_id": org_id, "since": since},
    )
    msg_rows = msg_result.fetchall()

    total_rag = sum(r.total for r in msg_rows)
    total_tokens = sum(r.tokens or 0 for r in msg_rows)
    avg_latency = (
        sum((r.avg_latency or 0) * r.total for r in msg_rows) / total_rag
        if total_rag else 0
    )

    # Estimated cost
    total_cost = sum(
        calculate_cost(r.llm_model, int(r.avg_prompt or 0), int(r.avg_compl or 0)) * r.total
        for r in msg_rows
    )

    # Agent runs in window
    agent_result = await db.execute(
        select(func.count(AgentRun.id))
        .where(
            AgentRun.organization_id == org_id,
            AgentRun.created_at >= since,
        )
    )
    total_agents = agent_result.scalar() or 0

    # Failed agent runs
    failed_result = await db.execute(
        select(func.count(AgentRun.id))
        .where(
            AgentRun.organization_id == org_id,
            AgentRun.created_at >= since,
            AgentRun.status == AgentRunStatus.FAILED,
        )
    )
    failed_agents = failed_result.scalar() or 0

    # Requests per hour (last 24h)
    hourly_result = await db.execute(
        text("""
            SELECT
                date_trunc('hour', m.created_at) AS hour,
                COUNT(*) AS count
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.organization_id = :org_id
              AND m.created_at >= :since
              AND m.llm_model IS NOT NULL
            GROUP BY hour
            ORDER BY hour
        """),
        {"org_id": org_id, "since": since},
    )
    hourly = [
        {"hour": str(r.hour), "count": r.count}
        for r in hourly_result
    ]

    top_models = [
        {
            "model": r.llm_model,
            "provider": r.llm_provider,
            "queries": r.total,
            "avg_latency_ms": round(float(r.avg_latency or 0), 1),
        }
        for r in sorted(msg_rows, key=lambda x: x.total, reverse=True)
    ]

    return {
        "period_hours": hours,
        "total_requests": total_rag + total_agents,
        "rag_requests": total_rag,
        "agent_requests": total_agents,
        "error_count": failed_agents,
        "avg_latency_ms": round(avg_latency, 1),
        "total_tokens": int(total_tokens),
        "estimated_cost_usd": round(total_cost, 4),
        "requests_by_hour": hourly,
        "top_models": top_models,
    }


@router.get("/mlflow-url")
async def get_mlflow_url():
    """Return the MLflow UI URL for deep linking from the dashboard."""
    # Exposed on host port 5001 via docker-compose
    return {"url": "http://localhost:5001", "tracking_uri": settings.mlflow_tracking_uri}
