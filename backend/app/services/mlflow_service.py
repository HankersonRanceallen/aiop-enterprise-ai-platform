"""
MLflow Service
===============
Wraps the MLflow tracking client with a safe, async-friendly interface.

Key principle: MLflow logging NEVER crashes the main application.
Every call is wrapped in try/except — if MLflow is down, requests still work.

What we track:
  - Every RAG query (prompt version, model, latency, tokens, cost)
  - Every agent run (per-step metrics + totals)
  - Evaluation results (faithfulness, relevance, completeness)
  - Model comparisons (for the V3 comparison table)

This is what lets interviewers see the MLflow UI showing:
  Model       Accuracy  Cost    Latency
  GPT-4o      92%       High    Medium
  Claude      90%       Medium  Medium
  Ollama      85%       Free    Slower
"""
import mlflow
from mlflow.tracking import MlflowClient

from app.core.config import settings

# Cost per 1M tokens (USD) — update as pricing changes
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o":                          {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini":                     {"input": 0.15,  "output": 0.60},
    "gpt-4-turbo":                     {"input": 10.00, "output": 30.00},
    "claude-3-5-sonnet-20241022":      {"input": 3.00,  "output": 15.00},
    "claude-3-5-haiku-20241022":       {"input": 0.80,  "output": 4.00},
    "claude-3-opus-20240229":          {"input": 15.00, "output": 75.00},
    "llama3.1":                        {"input": 0.00,  "output": 0.00},
    "qwen":                            {"input": 0.00,  "output": 0.00},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for a given LLM call."""
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    input_cost  = (prompt_tokens     / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def _get_or_create_experiment(name: str) -> str:
    """Return experiment ID, creating it if it doesn't exist."""
    client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
    experiment = client.get_experiment_by_name(name)
    if experiment is None:
        return client.create_experiment(name)
    return experiment.experiment_id


def log_rag_query(
    question: str,
    llm_provider: str,
    llm_model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    chunks_retrieved: int,
    organization_id: int,
    top_chunk_score: float = 0.0,
    prompt_version: str = "v1.0",
) -> None:
    """
    Log a single RAG query to MLflow.
    Called from rag/pipeline.py after every query.
    """
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        exp_id = _get_or_create_experiment(settings.mlflow_experiment_name)

        cost = calculate_cost(llm_model, prompt_tokens, completion_tokens)

        with mlflow.start_run(experiment_id=exp_id, run_name="rag_query"):
            # Parameters (what was used)
            mlflow.log_params({
                "query_type":       "rag",
                "llm_provider":     llm_provider,
                "llm_model":        llm_model,
                "prompt_version":   prompt_version,
                "organization_id":  organization_id,
            })

            # Metrics (what happened)
            mlflow.log_metrics({
                "prompt_tokens":      prompt_tokens,
                "completion_tokens":  completion_tokens,
                "total_tokens":       prompt_tokens + completion_tokens,
                "latency_ms":         latency_ms,
                "cost_usd":           cost,
                "chunks_retrieved":   chunks_retrieved,
                "top_chunk_score":    top_chunk_score,
            })

            # Tags for filtering in MLflow UI
            mlflow.set_tags({
                "query_type": "rag",
                "org_id":     str(organization_id),
            })

    except Exception:
        pass  # MLflow is never allowed to break the main flow


def log_agent_run(
    task: str,
    llm_provider: str,
    llm_model: str,
    total_tokens: int,
    latency_ms: float,
    step_log: list[dict],
    organization_id: int,
    succeeded: bool,
) -> None:
    """
    Log a full multi-agent run to MLflow.
    Called from agents/graph.py after the graph completes.
    """
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        exp_id = _get_or_create_experiment(settings.mlflow_experiment_name)

        cost = calculate_cost(llm_model, total_tokens // 2, total_tokens // 2)

        with mlflow.start_run(experiment_id=exp_id, run_name="agent_run"):
            mlflow.log_params({
                "query_type":      "agent",
                "llm_provider":    llm_provider,
                "llm_model":       llm_model,
                "num_agents":      len(step_log),
                "organization_id": organization_id,
            })

            mlflow.log_metrics({
                "total_tokens":  total_tokens,
                "latency_ms":    latency_ms,
                "cost_usd":      cost,
                "num_steps":     len(step_log),
                "succeeded":     1.0 if succeeded else 0.0,
            })

            # Log per-agent latencies
            for step in step_log:
                agent = step.get("agent", "unknown")
                mlflow.log_metric(f"latency_ms_{agent}", step.get("latency_ms", 0))

            mlflow.set_tags({
                "query_type": "agent",
                "org_id":     str(organization_id),
                "status":     "complete" if succeeded else "failed",
            })

    except Exception:
        pass


def log_evaluation(
    question: str,
    llm_model: str,
    faithfulness: float,
    relevance: float,
    completeness: float,
    organization_id: int,
) -> None:
    """
    Log an evaluation result to MLflow.
    Called from evaluation.py after scoring a RAG response.
    """
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        exp_name = f"{settings.mlflow_experiment_name}-eval"
        exp_id = _get_or_create_experiment(exp_name)

        composite = (faithfulness + relevance + completeness) / 3

        with mlflow.start_run(experiment_id=exp_id, run_name="evaluation"):
            mlflow.log_params({
                "llm_model":       llm_model,
                "organization_id": organization_id,
            })
            mlflow.log_metrics({
                "faithfulness":   faithfulness,
                "relevance":      relevance,
                "completeness":   completeness,
                "composite_score": composite,
            })
            mlflow.set_tags({"query_type": "evaluation"})

    except Exception:
        pass
