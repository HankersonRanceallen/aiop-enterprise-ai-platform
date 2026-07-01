"""
RAG Pipeline
=============
Orchestrates the full Retrieval-Augmented Generation flow:

  Question → Embed → Retrieve Chunks → Build Prompt → LLM → Answer + Sources

V3 addition: every query is logged to MLflow for experiment tracking.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm.base import BaseLLMService, LLMResponse
from app.services.rag.retriever import retrieve_chunks
from app.services.mlflow_service import log_rag_query
from app.core.config import settings


RAG_SYSTEM_PROMPT = """You are an intelligent assistant for an enterprise knowledge platform.
You answer questions based ONLY on the provided document context below.

Rules:
- Answer using only the information in the context.
- If the context doesn't contain enough information, say so clearly.
- Always cite which document(s) your answer comes from.
- Be concise, accurate, and professional.
- Format your answer clearly with markdown when helpful.

Context:
{context}
"""

# Increment this when the prompt changes — tracked in MLflow
PROMPT_VERSION = "v1.0"


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[{i}] From: \"{chunk['document_title']}\" (chunk {chunk['chunk_index']})\n"
            f"{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


async def run_rag_query(
    db: AsyncSession,
    llm: BaseLLMService,
    question: str,
    organization_id: int,
    conversation_history: list[dict] | None = None,
    document_ids: list[int] | None = None,
) -> dict:
    # Step 1: Embed the question
    embedding_response = await llm.embed(question)
    query_embedding = embedding_response.embedding

    # Step 2: Retrieve top-k relevant chunks
    chunks = await retrieve_chunks(
        db=db,
        query_embedding=query_embedding,
        organization_id=organization_id,
        top_k=settings.top_k_retrieval,
        document_ids=document_ids,
    )

    if not chunks:
        return {
            "answer": "I couldn't find any relevant information in the uploaded documents to answer your question.",
            "sources": [],
            "llm_provider": llm.provider_name,
            "llm_model": llm.model_name,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 0.0,
        }

    # Step 3: Build context and system prompt
    context = _build_context(chunks)
    system_prompt = RAG_SYSTEM_PROMPT.format(context=context)

    # Step 4: Build messages
    messages = []
    if conversation_history:
        messages.extend(conversation_history[-6:])
    messages.append({"role": "user", "content": question})

    # Step 5: Generate answer
    llm_response: LLMResponse = await llm.generate(
        messages=messages,
        system_prompt=system_prompt,
        temperature=0.1,
    )

    # Step 6 (V3): Log to MLflow — non-blocking, never raises
    top_score = chunks[0]["score"] if chunks else 0.0
    log_rag_query(
        question=question,
        llm_provider=llm_response.provider,
        llm_model=llm_response.model,
        prompt_tokens=llm_response.prompt_tokens,
        completion_tokens=llm_response.completion_tokens,
        latency_ms=llm_response.latency_ms,
        chunks_retrieved=len(chunks),
        organization_id=organization_id,
        top_chunk_score=top_score,
        prompt_version=PROMPT_VERSION,
    )

    return {
        "answer": llm_response.content,
        "sources": chunks,
        "llm_provider": llm_response.provider,
        "llm_model": llm_response.model,
        "prompt_tokens": llm_response.prompt_tokens,
        "completion_tokens": llm_response.completion_tokens,
        "latency_ms": llm_response.latency_ms,
    }
