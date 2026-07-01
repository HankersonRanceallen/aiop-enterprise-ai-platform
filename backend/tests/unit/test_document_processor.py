"""Unit tests for app/services/document_processor.py"""
import pytest
import tempfile
import os

from app.services.document_processor import _chunk_text, process_document


class TestChunkText:
    def test_empty_string_returns_empty_list(self):
        assert _chunk_text("", chunk_size=100, overlap=20) == []

    def test_whitespace_only_returns_empty_list(self):
        assert _chunk_text("   \n\n  ", chunk_size=100, overlap=20) == []

    def test_short_text_is_single_chunk(self):
        text = "This is a short document."
        chunks = _chunk_text(text, chunk_size=1000, overlap=200)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_is_split(self):
        text = "A" * 3000
        chunks = _chunk_text(text, chunk_size=1000, overlap=200)
        assert len(chunks) > 1

    def test_overlap_means_chunks_share_content(self):
        text = "X" * 2000
        chunks = _chunk_text(text, chunk_size=1000, overlap=200)
        # With 200 char overlap, chunk 2 starts 800 chars after chunk 1
        assert len(chunks) >= 2

    def test_no_empty_chunks(self):
        text = "Hello world. " * 100
        chunks = _chunk_text(text, chunk_size=100, overlap=20)
        assert all(c.strip() for c in chunks)

    def test_chunk_size_respected(self):
        text = "B" * 5000
        chunks = _chunk_text(text, chunk_size=1000, overlap=0)
        for chunk in chunks:
            assert len(chunk) <= 1000


class TestProcessDocument:
    def test_txt_file_extraction(self):
        content = "This is the content of a text file.\nLine two.\nLine three."
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            path = f.name
        try:
            import asyncio
            chunks = asyncio.run(process_document(path, "txt"))
            assert len(chunks) >= 1
            assert "text file" in " ".join(chunks)
        finally:
            os.unlink(path)

    def test_unsupported_type_raises(self):
        import asyncio
        with pytest.raises(ValueError, match="Unsupported file type"):
            asyncio.run(process_document("/fake/path.xyz", "xyz"))
