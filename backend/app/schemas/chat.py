from datetime import datetime
from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str


class SourceChunk(BaseModel):
    document_id: int
    document_title: str
    chunk_index: int
    content: str
    score: float


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    sources: list[SourceChunk]
    llm_provider: str
    llm_model: str
    latency_ms: float


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: list | None
    llm_provider: str | None
    llm_model: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]
