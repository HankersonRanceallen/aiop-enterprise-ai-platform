"""
Evaluation Service — LLM-as-Judge
====================================
Implements RAGAS-style evaluation metrics using the LLM itself as the judge.

Three metrics:
  - Faithfulness:   Does the answer ONLY use info from the context?
  - Relevance:      Does the answer actually address the question?
  - Completeness:   Does the answer cover all aspects of the question?

Each scored 0.0–1.0. Results are logged to MLflow and stored in the DB.

Why LLM-as-judge?
  Traditional NLP metrics (BLEU, ROUGE) don't capture semantic quality.
  An LLM judge evaluates meaning, not just word overlap — much closer
  to how a human expert would score the response.
  This is the same approach used by OpenAI Evals, RAGAS, and HellaSwag.
"""
import json
from dataclasses import dataclass

from app.services.llm.base import BaseLLMService


@dataclass
class EvaluationResult:
    faithfulness: float      # 0-1: answer grounded in context?
    relevance: float         # 0-1: answer addresses the question?
    completeness: float      # 0-1: answer covers all aspects?
    composite: float         # average of the three
    reasoning: dict[str, str]  # per-metric explanation


FAITHFULNESS_PROMPT = """You are an expert AI evaluation judge.

Evaluate FAITHFULNESS: Does the answer contain ONLY information supported by the context?
A faithful answer makes no claims beyond what the context contains.

Score 0.0 to 1.0:
  1.0 = Every claim in the answer is directly supported by the context
  0.7 = Most claims supported, minor unsupported additions
  0.5 = Half supported, half from outside the context
  0.0 = Answer ignores or contradicts the context

Question: {question}

Context:
{context}

Answer: {answer}

Respond with ONLY valid JSON (no markdown):
{{"score": 0.85, "reason": "One sentence explanation"}}"""


RELEVANCE_PROMPT = """You are an expert AI evaluation judge.

Evaluate RELEVANCE: Does the answer directly address what was asked?
A relevant answer stays on topic and answers the specific question.

Score 0.0 to 1.0:
  1.0 = Answer directly and completely addresses the question
  0.7 = Mostly addresses the question with some tangents
  0.5 = Partially answers the question
  0.0 = Answer is off-topic or doesn't address the question

Question: {question}
Answer: {answer}

Respond with ONLY valid JSON (no markdown):
{{"score": 0.90, "reason": "One sentence explanation"}}"""


COMPLETENESS_PROMPT = """You are an expert AI evaluation judge.

Evaluate COMPLETENESS: Does the answer cover all important aspects of the question?
A complete answer addresses the full scope of what was asked.

Score 0.0 to 1.0:
  1.0 = All aspects of the question are addressed
  0.7 = Most aspects covered, minor omissions
  0.5 = Key aspects missing
  0.0 = Answer barely touches the question

Question: {question}
Answer: {answer}

Respond with ONLY valid JSON (no markdown):
{{"score": 0.75, "reason": "One sentence explanation"}}"""


def _format_context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[{i+1}] {c['content']}" for i, c in enumerate(chunks[:5])
    )


async def _score(llm: BaseLLMService, prompt: str) -> tuple[float, str]:
    """Call LLM with an evaluation prompt, parse JSON score."""
    try:
        response = await llm.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=150,
        )
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)
        score = float(data.get("score", 0.5))
        reason = str(data.get("reason", ""))
        return max(0.0, min(1.0, score)), reason
    except Exception:
        return 0.5, "Could not evaluate"


async def evaluate_rag_response(
    llm: BaseLLMService,
    question: str,
    answer: str,
    retrieved_chunks: list[dict],
) -> EvaluationResult:
    """
    Run all three evaluation metrics on a RAG response.

    Args:
        llm:               Any BaseLLMService — uses same provider as the query
        question:          The user's original question
        answer:            The LLM's answer
        retrieved_chunks:  The chunks used to generate the answer

    Returns:
        EvaluationResult with per-metric scores and reasoning
    """
    context = _format_context(retrieved_chunks)

    # Run all three evaluations
    faith_score, faith_reason = await _score(
        llm, FAITHFULNESS_PROMPT.format(
            question=question, context=context, answer=answer
        )
    )

    rel_score, rel_reason = await _score(
        llm, RELEVANCE_PROMPT.format(question=question, answer=answer)
    )

    comp_score, comp_reason = await _score(
        llm, COMPLETENESS_PROMPT.format(question=question, answer=answer)
    )

    composite = round((faith_score + rel_score + comp_score) / 3, 3)

    return EvaluationResult(
        faithfulness=round(faith_score, 3),
        relevance=round(rel_score, 3),
        completeness=round(comp_score, 3),
        composite=composite,
        reasoning={
            "faithfulness": faith_reason,
            "relevance":    rel_reason,
            "completeness": comp_reason,
        },
    )
