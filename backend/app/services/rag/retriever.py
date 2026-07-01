"""
RAG Retriever
==============
Performs cosine similarity search against document chunks in pgvector.
Returns the top-k most relevant chunks for a given question embedding.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.models.document import DocumentChunk, Document, DocumentStatus


async def retrieve_chunks(
    db: AsyncSession,
    query_embedding: list[float],
    organization_id: int,
    top_k: int = 5,
    document_ids: list[int] | None = None,
) -> list[dict]:
    """
    Find the most relevant document chunks using cosine similarity.

    Args:
        db: Async database session
        query_embedding: Vector embedding of the user's question
        organization_id: Restrict search to this org's documents
        top_k: Number of chunks to return
        document_ids: Optional filter to specific documents

    Returns:
        List of chunk dicts with content, score, and document metadata
    """
    # Build the query using pgvector cosine distance operator (<=>)
    # Lower distance = more similar
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    base_query = """
        SELECT
            dc.id,
            dc.document_id,
            dc.chunk_index,
            dc.content,
            d.title AS document_title,
            1 - (dc.embedding <=> :embedding::vector) AS score
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.organization_id = :org_id
          AND d.status = 'ready'
          AND dc.embedding IS NOT NULL
    """

    params: dict = {"embedding": embedding_str, "org_id": organization_id}

    if document_ids:
        base_query += " AND dc.document_id = ANY(:doc_ids)"
        params["doc_ids"] = document_ids

    base_query += " ORDER BY dc.embedding <=> :embedding::vector LIMIT :top_k"
    params["top_k"] = top_k

    result = await db.execute(text(base_query), params)
    rows = result.fetchall()

    return [
        {
            "id": row.id,
            "document_id": row.document_id,
            "document_title": row.document_title,
            "chunk_index": row.chunk_index,
            "content": row.content,
            "score": float(row.score),
        }
        for row in rows
    ]
