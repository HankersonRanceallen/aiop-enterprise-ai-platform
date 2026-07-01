from datetime import datetime
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    title: str
    filename: str
    file_type: str
    file_size_bytes: int
    status: str
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentOut]
    total: int
