"""
Document Processor
===================
Extracts plain text from uploaded files and splits into
overlapping chunks for embedding.
"""
import os
from pathlib import Path

import aiofiles
from pypdf import PdfReader
from docx import Document as DocxDocument

from app.core.config import settings


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split text into overlapping chunks.
    Simple character-based splitting — in Phase 3 we'll add
    semantic chunking with sentence boundaries.
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def _extract_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def _extract_docx(file_path: str) -> str:
    doc = DocxDocument(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


async def process_document(file_path: str, file_type: str) -> list[str]:
    """
    Extract text from a document file and return a list of chunks.

    Args:
        file_path: Absolute path to the file on disk
        file_type: One of 'pdf', 'docx', 'txt'

    Returns:
        List of text chunks ready for embedding
    """
    ext = file_type.lower().strip(".")

    if ext == "pdf":
        text = _extract_pdf(file_path)
    elif ext in ("docx", "doc"):
        text = _extract_docx(file_path)
    elif ext == "txt":
        text = _extract_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    chunks = _chunk_text(
        text,
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )
    return chunks
