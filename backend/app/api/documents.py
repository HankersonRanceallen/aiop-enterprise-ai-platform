import os
import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import aiofiles

from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.user import User
from app.schemas.document import DocumentListResponse, DocumentOut
from app.api.deps import get_current_user
from app.services.document_processor import process_document
from app.services.llm.factory import get_llm_service

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {"pdf", "docx", "txt"}


async def _ingest_document(document_id: int, file_path: str, file_type: str) -> None:
    """
    Background task: extract text, embed chunks, store in pgvector.
    Runs after the upload response is returned to the user.
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import update

    async with AsyncSessionLocal() as db:
        try:
            # Update status to processing
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(status=DocumentStatus.PROCESSING)
            )
            await db.commit()

            # Extract + chunk text
            chunks = await process_document(file_path, file_type)

            # Embed each chunk
            llm = get_llm_service()
            chunk_records = []

            for i, chunk_text in enumerate(chunks):
                embedding_response = await llm.embed(chunk_text)
                chunk_records.append(
                    DocumentChunk(
                        document_id=document_id,
                        chunk_index=i,
                        content=chunk_text,
                        embedding=embedding_response.embedding,
                    )
                )

            db.add_all(chunk_records)

            # Mark ready
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    status=DocumentStatus.READY,
                    chunk_count=len(chunk_records),
                )
            )
            await db.commit()

        except Exception as e:
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(status=DocumentStatus.FAILED)
            )
            await db.commit()
            raise e


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must belong to an organization to upload documents",
        )

    # Validate file type
    extension = file.filename.split(".")[-1].lower() if file.filename else ""
    if extension not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    # Read file
    content = await file.read()
    file_size = len(content)

    if file_size > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_file_size_mb}MB limit",
        )

    # Save to disk
    upload_dir = Path(settings.upload_dir) / str(current_user.organization_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{current_user.id}_{file.filename}"
    file_path = str(upload_dir / safe_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create document record
    document = Document(
        title=file.filename,
        filename=file.filename,
        file_path=file_path,
        file_type=extension,
        file_size_bytes=file_size,
        status=DocumentStatus.PENDING,
        organization_id=current_user.organization_id,
        uploaded_by=current_user.id,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Kick off background ingestion (embed + index)
    background_tasks.add_task(
        _ingest_document, document.id, file_path, extension
    )

    return document


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        return DocumentListResponse(documents=[], total=0)

    result = await db.execute(
        select(Document)
        .where(Document.organization_id == current_user.organization_id)
        .order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=list(documents),
        total=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == current_user.organization_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == current_user.organization_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    try:
        os.remove(doc.file_path)
    except FileNotFoundError:
        pass

    await db.delete(doc)
    await db.commit()
