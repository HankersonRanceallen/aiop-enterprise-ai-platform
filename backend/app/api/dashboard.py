from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.core.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id

    # Document counts
    doc_result = await db.execute(
        select(
            func.count(Document.id).label("total"),
            func.count(Document.id)
            .filter(Document.status == DocumentStatus.READY)
            .label("ready"),
            func.count(Document.id)
            .filter(Document.status == DocumentStatus.PROCESSING)
            .label("processing"),
            func.sum(Document.chunk_count).label("total_chunks"),
            func.sum(Document.file_size_bytes).label("total_bytes"),
        ).where(Document.organization_id == org_id)
    )
    doc_stats = doc_result.one()

    # Conversation/query counts
    conv_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.organization_id == org_id
        )
    )
    total_conversations = conv_result.scalar() or 0

    msg_result = await db.execute(
        select(func.count(Message.id)).join(
            Conversation, Message.conversation_id == Conversation.id
        ).where(Conversation.organization_id == org_id)
    )
    total_messages = msg_result.scalar() or 0

    # Token usage
    token_result = await db.execute(
        select(
            func.sum(Message.prompt_tokens).label("prompt_tokens"),
            func.sum(Message.completion_tokens).label("completion_tokens"),
        ).join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.organization_id == org_id)
    )
    token_stats = token_result.one()

    # Recent LLM providers used
    provider_result = await db.execute(
        select(Message.llm_provider, func.count(Message.id).label("count"))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.organization_id == org_id,
            Message.llm_provider.is_not(None),
        )
        .group_by(Message.llm_provider)
    )
    provider_usage = {row.llm_provider: row.count for row in provider_result}

    return {
        "documents": {
            "total": doc_stats.total or 0,
            "ready": doc_stats.ready or 0,
            "processing": doc_stats.processing or 0,
            "total_chunks": int(doc_stats.total_chunks or 0),
            "total_size_mb": round((doc_stats.total_bytes or 0) / (1024 * 1024), 2),
        },
        "queries": {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
        },
        "tokens": {
            "prompt_tokens": int(token_stats.prompt_tokens or 0),
            "completion_tokens": int(token_stats.completion_tokens or 0),
            "total_tokens": int((token_stats.prompt_tokens or 0) + (token_stats.completion_tokens or 0)),
        },
        "providers": provider_usage,
    }
