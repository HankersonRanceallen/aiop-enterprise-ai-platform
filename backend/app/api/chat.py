from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.conversation import Conversation, Message, MessageRole
from app.models.user import User
from app.schemas.chat import (
    ChatRequest, ChatResponse, ConversationDetailOut,
    ConversationOut, MessageOut, SourceChunk,
)
from app.api.deps import get_current_user
from app.services.llm.factory import get_llm_service
from app.services.rag.pipeline import run_rag_query

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def send_message(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Join an organization before chatting",
        )

    # Get or create conversation
    if payload.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == payload.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Title = first 60 chars of the question
        title = payload.message[:60] + ("…" if len(payload.message) > 60 else "")
        conversation = Conversation(
            title=title,
            user_id=current_user.id,
            organization_id=current_user.organization_id,
        )
        db.add(conversation)
        await db.flush()

    # Load conversation history for multi-turn context
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    history = history_result.scalars().all()
    history_messages = [
        {"role": msg.role.value, "content": msg.content} for msg in history
    ]

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=payload.message,
    )
    db.add(user_msg)
    await db.flush()

    # Run RAG pipeline
    llm = get_llm_service()
    result_data = await run_rag_query(
        db=db,
        llm=llm,
        question=payload.message,
        organization_id=current_user.organization_id,
        conversation_history=history_messages,
    )

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=result_data["answer"],
        sources=[
            {
                "document_id": s["document_id"],
                "document_title": s["document_title"],
                "chunk_index": s["chunk_index"],
                "content": s["content"][:300],
                "score": s["score"],
            }
            for s in result_data["sources"]
        ],
        llm_provider=result_data["llm_provider"],
        llm_model=result_data["llm_model"],
        prompt_tokens=result_data["prompt_tokens"],
        completion_tokens=result_data["completion_tokens"],
        latency_ms=int(result_data["latency_ms"]),
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
        answer=result_data["answer"],
        sources=[
            SourceChunk(
                document_id=s["document_id"],
                document_title=s["document_title"],
                chunk_index=s["chunk_index"],
                content=s["content"],
                score=s["score"],
            )
            for s in result_data["sources"]
        ],
        llm_provider=result_data["llm_provider"],
        llm_model=result_data["llm_model"],
        latency_ms=result_data["latency_ms"],
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()
