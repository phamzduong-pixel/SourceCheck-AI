"""Comprehensive unit and integration test suite for Document Ingestion Foundation.

Tests:
- Parsers: TXT, PDF, DOCX (with synthetic files and error handling)
- TextCleaner: Deterministic normalization and noise reduction
- MetadataExtractor: SHA-256, page/word/char counting, metadata merging
- Chunkers: FixedSizeChunker, SentenceWindowChunker (page preservation)
- IngestionService: Full transactional pipeline, validation, and rollback
- API Routers: /documents/upload and /documents/ingest
"""

import io
import uuid
import docx
import pytest
from pypdf import PdfWriter
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from pgvector.sqlalchemy import Vector

# SQLite compiler compatibility hooks for isolated in-memory testing
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"


from app.core.config import settings
from app.core.exceptions import (
    DocumentParsingException,
    EmptyDocumentException,
    FileTooLargeException,
    UnsupportedFileTypeException,
)
from app.models.base import Base
from app.models.document import Document, DocumentChunk
from app.services.ingestion.chunkers import (
    FixedSizeChunker,
    SentenceWindowChunker,
    get_chunker,
)
from app.services.ingestion.cleaners import TextCleaner
from app.services.ingestion.ingestion_service import IngestionService
from app.services.ingestion.metadata import MetadataExtractor
from app.services.ingestion.parsers import (
    DocxParser,
    PdfParser,
    TxtParser,
    get_parser_for_file,
)


# --- Helper: Generate Synthetic PDF with Text ---
SAMPLE_TWO_PAGE_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>
endobj
4 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
6 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
72 712 Td
(Page 1 Fact Check) Tj
ET
endstream
endobj
7 0 obj
<< /Length 46 >>
stream
BT
/F1 12 Tf
72 712 Td
(Page 2 Verified Text) Tj
ET
endstream
endobj
xref
0 8
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000121 00000 n 
0000000244 00000 n 
0000000367 00000 n 
0000000434 00000 n 
0000000527 00000 n 
trailer
<< /Size 8 /Root 1 0 R >>
startxref
622
%%EOF"""



# --- Helper: Generate Synthetic DOCX ---
def create_synthetic_docx(paragraphs: list[str], table_rows: list[list[str]] = None) -> bytes:
    """Create in-memory DOCX with specified paragraphs and table rows."""
    doc = docx.Document()
    doc.core_properties.title = "Synthetic Test Document"
    doc.core_properties.author = "SourceCheck Test Suite"
    
    for p in paragraphs:
        doc.add_paragraph(p)
        
    if table_rows:
        table = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
        for r_idx, row in enumerate(table_rows):
            for c_idx, cell_value in enumerate(row):
                table.cell(r_idx, c_idx).text = cell_value
                
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


import pytest_asyncio


# --- Fixtures ---
@pytest_asyncio.fixture
async def async_session():
    """Create an async in-memory SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session_factory() as session:
        yield session
    
    await engine.dispose()



# --- Tests: Parsers ---
def test_txt_parser_utf8():
    parser = TxtParser()
    content = "SourceCheck AI is an automated fact-checking system.\nIt analyzes claims against evidence.".encode("utf-8")
    doc = parser.parse(content, "test.txt")
    
    assert doc.file_type == "txt"
    assert len(doc.pages) == 1
    assert doc.pages[0].page_number == 1
    assert "SourceCheck AI" in doc.full_text
    assert doc.metadata["encoding"] == "utf-8"


def test_txt_parser_latin1_fallback():
    parser = TxtParser()
    content = "Café au lait and naïve assumptions.".encode("latin-1")
    doc = parser.parse(content, "french.txt")
    
    assert doc.file_type == "txt"
    assert "Café" in doc.full_text


def test_docx_parser_content_and_tables():
    paragraphs = [
        "First paragraph introducing the verification subject.",
        "Second paragraph with statistical figures: GDP grew by 5.2%.",
    ]
    tables = [
        ["Quarter", "Growth"],
        ["Q1", "5.1%"],
        ["Q2", "5.3%"],
    ]
    docx_bytes = create_synthetic_docx(paragraphs, tables)
    
    parser = DocxParser()
    doc = parser.parse(docx_bytes, "report.docx")
    
    assert doc.file_type == "docx"
    assert len(doc.pages) == 1
    assert doc.pages[0].page_number == 1
    assert "First paragraph" in doc.full_text
    assert "GDP grew by 5.2%" in doc.full_text
    assert "Quarter | Growth" in doc.full_text
    assert doc.metadata["title"] == "Synthetic Test Document"
    assert doc.metadata["author"] == "SourceCheck Test Suite"


def test_docx_parser_corrupted_file():
    parser = DocxParser()
    with pytest.raises(DocumentParsingException):
        parser.parse(b"corrupted bytes that are not zip or docx", "bad.docx")


def test_pdf_parser_corrupted_file():
    parser = PdfParser()
    with pytest.raises(DocumentParsingException):
        parser.parse(b"not a valid pdf header", "bad.pdf")


def test_pdf_parser_multi_page_extraction():
    parser = PdfParser()
    doc = parser.parse(SAMPLE_TWO_PAGE_PDF, "sample.pdf")
    
    assert doc.file_type == "pdf"
    assert len(doc.pages) == 2
    assert doc.pages[0].page_number == 1
    assert "Page 1 Fact Check" in doc.pages[0].text
    assert doc.pages[1].page_number == 2
    assert "Page 2 Verified Text" in doc.pages[1].text
    assert doc.metadata["page_count"] == 2



def test_parser_factory_unsupported_type():
    with pytest.raises(UnsupportedFileTypeException) as exc_info:
        get_parser_for_file("executable.exe")
    assert exc_info.value.code == "UNSUPPORTED_FILE_TYPE"


# --- Tests: TextCleaner ---
def test_text_cleaner_deterministic_normalization():
    dirty_text = "  Hello \t\t world!  \r\n\r\n\r\nThis has \x00 control chars and   excessive   spaces.   \n\n\n\nEnd. "
    cleaned = TextCleaner.clean(dirty_text)
    
    assert "\x00" not in cleaned
    assert "\t" not in cleaned
    assert "   " not in cleaned
    assert "\r" not in cleaned
    # Max consecutive newlines is 2
    assert "\n\n\n" not in cleaned
    assert cleaned.startswith("Hello world!")
    assert cleaned.endswith("End.")


# --- Tests: MetadataExtractor ---
def test_metadata_extractor():
    parser = TxtParser()
    raw = b"Fact verification requires traceable evidence."
    parsed_doc = parser.parse(raw, "source_doc.txt")
    
    metadata = MetadataExtractor.extract(
        parsed_doc=parsed_doc,
        raw_content=raw,
        custom_metadata={"publisher": "Reuters", "category": "News"},
    )
    
    assert metadata["filename"] == "source_doc.txt"
    assert metadata["file_type"] == "txt"
    assert metadata["file_size_bytes"] == len(raw)
    assert len(metadata["sha256"]) == 64  # SHA-256 hex string length
    assert metadata["word_count"] == 5
    assert metadata["page_count"] == 1
    assert metadata["publisher"] == "Reuters"
    assert metadata["category"] == "News"
    assert "ingested_at" in metadata


# --- Tests: Chunkers ---
def test_fixed_size_chunker_page_retention():
    # Simulate a 2-page document
    parser = TxtParser()
    raw = b"First page long text content. " * 30 + b"\n\nSecond page text content. " * 30
    parsed = parser.parse(raw, "doc.txt")
    # Manually split into 2 pages for testing
    from app.services.ingestion.parsers.base import PageContent
    parsed.pages = [
        PageContent(page_number=1, text="Page 1 sentence one. Page 1 sentence two. Page 1 sentence three."),
        PageContent(page_number=2, text="Page 2 sentence one. Page 2 sentence two. Page 2 sentence three."),
    ]
    
    chunker = FixedSizeChunker(chunk_size=40, chunk_overlap=10)
    chunks = chunker.chunk(parsed)
    
    assert len(chunks) > 0
    # Chunks from page 1 must have page_number == 1
    # Chunks from page 2 must have page_number == 2
    p1_chunks = [c for c in chunks if c.page_number == 1]
    p2_chunks = [c for c in chunks if c.page_number == 2]
    assert len(p1_chunks) > 0
    assert len(p2_chunks) > 0
    
    # Sequential chunk indexing
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.token_count > 0
        assert c.char_start >= 0
        assert c.char_end > c.char_start


def test_sentence_window_chunker():
    parser = TxtParser()
    text = "First sentence is clear. Second sentence has details. Third sentence concludes. Fourth sentence follows."
    parsed = parser.parse(text.encode("utf-8"), "test.txt")
    
    chunker = SentenceWindowChunker(window_size=1)
    chunks = chunker.chunk(parsed)
    
    assert len(chunks) == 4
    # The second chunk's window should contain first, second, and third sentences
    assert chunks[1].content == "Second sentence has details."
    assert "First sentence is clear." in chunks[1].metadata["window"]
    assert "Third sentence concludes." in chunks[1].metadata["window"]
    assert chunks[1].page_number == 1


# --- Tests: IngestionService Transactional Flow ---
@pytest.mark.asyncio
async def test_ingestion_service_success(async_session: AsyncSession):
    service = IngestionService(default_chunk_strategy="fixed")
    
    content = (
        "Artificial Intelligence in Healthcare.\n\n"
        "Machine learning models are increasingly deployed to assist in medical imaging diagnosis.\n"
        "Clinical trials demonstrate high sensitivity in detecting early-stage lesions."
    ).encode("utf-8")
    
    result = await service.ingest_document(
        content=content,
        filename="ai_healthcare.txt",
        session=async_session,
        custom_metadata={"domain": "biomedical"},
    )
    
    assert result["document_id"] is not None
    assert result["title"] == "ai_healthcare"
    assert result["doc_type"] == "txt"
    assert result["total_chunks"] > 0
    
    # Verify database persistence
    doc_id = uuid.UUID(result["document_id"])
    db_doc = await async_session.get(Document, doc_id)
    assert db_doc is not None
    assert db_doc.title == "ai_healthcare"
    assert "biomedical" in db_doc.doc_metadata.get("domain")
    
    # Verify DocumentChunks in DB
    query = select(DocumentChunk).where(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.chunk_index)
    res = await async_session.execute(query)
    db_chunks = res.scalars().all()
    
    assert len(db_chunks) == result["total_chunks"]
    for chunk in db_chunks:
        # Embedding must be None at this foundation stage
        assert chunk.embedding is None
        # Page context and offsets must be stored in chunk_metadata
        assert "page_number" in chunk.chunk_metadata
        assert "char_start" in chunk.chunk_metadata
        assert "char_end" in chunk.chunk_metadata
        assert chunk.token_count > 0


@pytest.mark.asyncio
async def test_ingestion_service_empty_document(async_session: AsyncSession):
    service = IngestionService()
    empty_content = b"   \n\n\t   "
    
    with pytest.raises(EmptyDocumentException):
        await service.ingest_document(
            content=empty_content,
            filename="empty.txt",
            session=async_session,
        )


@pytest.mark.asyncio
async def test_ingestion_service_file_too_large():
    service = IngestionService()
    huge_content = b"A" * (settings.MAX_UPLOAD_FILE_SIZE_BYTES + 1024)
    
    with pytest.raises(FileTooLargeException):
        service.validate_file("large.txt", len(huge_content))


@pytest.mark.asyncio
async def test_ingestion_docx_end_to_end(async_session: AsyncSession):
    service = IngestionService(default_chunk_strategy="sentence_window")
    docx_bytes = create_synthetic_docx(
        paragraphs=[
            "Verification of monetary policy statements.",
            "The central bank lowered the benchmark interest rate by 25 basis points.",
            "Inflation subsided to 2.4% over the past quarter.",
        ]
    )
    
    result = await service.ingest_document(
        content=docx_bytes,
        filename="monetary_policy.docx",
        session=async_session,
        chunk_strategy="sentence_window",
    )
    
    assert result["doc_type"] == "docx"
    assert result["total_chunks"] >= 3
    assert result["metadata"]["title"] == "Synthetic Test Document"


# --- Tests: FastAPI Endpoints ---
from fastapi.testclient import TestClient
from app.api.dependencies import get_db
from app.main import app


def test_api_upload_document(async_session: AsyncSession):
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        files = {
            "file": ("press_release.txt", b"Central Bank confirms 0.5% growth rate for Q2.", "text/plain")
        }
        url = f"{settings.API_V1_PREFIX}/documents/upload"
        response = client.post(url, files=files, data={"chunk_strategy": "fixed"})
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "press_release"
        assert data["data"]["total_chunks"] >= 1
        assert len(data["data"]["chunks"]) >= 1
    finally:
        app.dependency_overrides.clear()


def test_api_upload_unsupported_file(async_session: AsyncSession):
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        files = {
            "file": ("malware.exe", b"MZbinarycode", "application/octet-stream")
        }
        url = f"{settings.API_V1_PREFIX}/documents/upload"
        response = client.post(url, files=files)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    finally:
        app.dependency_overrides.clear()


def test_api_ingest_raw_text(async_session: AsyncSession):
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        payload = {
            "title": "Macroeconomic Outlook",
            "raw_content": "Inflation expectations remain anchored around 2 percent.",
            "source_url": "https://example.org/report",
            "publisher": "Federal Reserve",
            "doc_type": "text",
        }
        url = f"{settings.API_V1_PREFIX}/documents/ingest"
        response = client.post(url, json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "Macroeconomic Outlook"
        assert data["data"]["chunk_count"] >= 1
    finally:
        app.dependency_overrides.clear()


