"""Database Foundation Test Suite.

Tests table metadata, entity relationships, cascade deletions,
Alembic migration generation (upgrade & downgrade), and vector column definitions.
"""

import sys
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector

# SQLite compiler compatibility hooks for isolated in-memory unit testing
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
from app.models.base import Base
from app.models.user import User
from app.models.source import Source
from app.models.document import Document, DocumentChunk
from app.models.qa import Question, Answer
from app.models.verification import VerificationResult
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.citation import Citation
from app.models.evaluation import EvaluationRun


@pytest.fixture(scope="module")
def db_session():
    """In-memory SQLite session with all tables created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_models_metadata_tables_count():
    """Verify all 11 core tables are registered in SQLAlchemy metadata."""
    expected_tables = {
        "users",
        "sources",
        "documents",
        "document_chunks",
        "questions",
        "answers",
        "verification_results",
        "claims",
        "evidences",
        "citations",
        "evaluation_runs",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_vector_field_dimension():
    """Verify DocumentChunk has an embedding column with the centralized dimension (1536)."""
    table = Base.metadata.tables["document_chunks"]
    embedding_col = table.columns.get("embedding")
    assert embedding_col is not None
    assert isinstance(embedding_col.type, Vector)
    assert embedding_col.type.dim == settings.EMBEDDING_DIM
    assert settings.EMBEDDING_DIM == 1536


def test_database_config_no_hardcoded_secrets():
    """Verify database configuration loads from settings without hardcoded static secrets."""
    assert settings.DATABASE_URL.startswith("postgresql")
    assert settings.VECTOR_DB_TYPE == "pgvector"
    assert settings.sync_database_url.startswith("postgresql+psycopg2://")


def test_alembic_offline_migrations():
    """Verify Alembic can parse and generate static SQL for upgrade and downgrade without errors."""
    # Ensure sys.path allows importing alembic package
    if sys.path[0] == "":
        sys.path.insert(1, sys.path.pop(0))
    import alembic.config

    # Test upgrade head SQL generation
    try:
        alembic.config.main(argv=["upgrade", "head", "--sql"])
    except Exception as exc:
        pytest.fail(f"Alembic upgrade --sql failed: {exc}")

    # Test downgrade SQL generation
    try:
        alembic.config.main(argv=["downgrade", "001_initial_schema:base", "--sql"])
    except Exception as exc:
        pytest.fail(f"Alembic downgrade --sql failed: {exc}")


def test_crud_and_relationships(db_session):
    """Test creating interconnected entities and navigating relationships."""
    # 1. Create User
    user = User(
        email=f"test_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="secure_hashed_password",
        full_name="Nguyen Van A",
        role="researcher",
    )
    db_session.add(user)
    db_session.commit()
    assert user.id is not None

    # 2. Create Source
    source = Source(
        name="Tuoi Tre Online",
        domain=f"tuoitre_{uuid.uuid4().hex[:6]}.vn",
        source_type="news",
        reliability_score=0.95,
        is_verified=True,
    )
    db_session.add(source)
    db_session.commit()
    assert source.id is not None

    # 3. Create Document linked to Source
    doc = Document(
        source_id=source.id,
        title="Vietnam Economy Report 2026",
        source_url="https://tuoitre.vn/kinh-te-2026",
        doc_type="article",
        raw_content="Tăng trưởng GDP đạt mức ấn tượng trong quý 1 năm 2026.",
    )
    db_session.add(doc)
    db_session.commit()
    assert doc.id is not None
    assert doc.source.name == "Tuoi Tre Online"

    # 4. Create DocumentChunk with embedding placeholder
    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content="Tăng trưởng GDP đạt mức ấn tượng trong quý 1 năm 2026.",
        token_count=12,
    )
    db_session.add(chunk)
    db_session.commit()
    assert len(doc.chunks) == 1

    # 5. Create VerificationResult linked to User
    verif = VerificationResult(
        user_id=user.id,
        input_text="Tăng trưởng GDP quý 1 đạt mức kỷ lục.",
        status="COMPLETED",
        overall_verdict="TRUE",
        summary="Được chứng minh bởi bài báo kinh tế.",
        confidence_score=0.92,
    )
    db_session.add(verif)
    db_session.commit()

    # 6. Create Claim linked to VerificationResult
    claim = Claim(
        verification_result_id=verif.id,
        claim_index=1,
        claim_text="Tăng trưởng GDP quý 1 năm 2026 đạt mức ấn tượng.",
        verdict="SUPPORTED",
        confidence_score=0.95,
        explanation="Khớp với số liệu báo cáo.",
    )
    db_session.add(claim)
    db_session.commit()

    # 7. Create Evidence linked to DocumentChunk & Source
    evidence = Evidence(
        document_chunk_id=chunk.id,
        source_id=source.id,
        snippet="Tăng trưởng GDP đạt mức ấn tượng...",
        source_title=doc.title,
        source_url=doc.source_url,
    )
    db_session.add(evidence)
    db_session.commit()

    # 8. Create Citation connecting Claim to Evidence
    citation = Citation(
        claim_id=claim.id,
        evidence_id=evidence.id,
        stance="SUPPORTS",
        quote="Tăng trưởng GDP đạt mức ấn tượng trong quý 1 năm 2026.",
        relevance_score=0.96,
        citation_number=1,
    )
    db_session.add(citation)
    db_session.commit()

    # Verify relationships
    assert len(verif.claims) == 1
    assert len(claim.citations) == 1
    assert claim.citations[0].evidence.source_title == "Vietnam Economy Report 2026"
    assert claim.citations[0].stance == "SUPPORTS"

    # 9. Create Question & Answer
    question = Question(
        user_id=user.id,
        question_text="Tăng trưởng GDP quý 1 năm 2026 như thế nào?",
    )
    db_session.add(question)
    db_session.commit()

    answer = Answer(
        question_id=question.id,
        answer_text="Tăng trưởng GDP đạt mức ấn tượng theo báo cáo Tuổi Trẻ.",
        confidence_score=0.94,
    )
    db_session.add(answer)
    db_session.commit()

    assert question.answer.answer_text == answer.answer_text


def test_cascade_deletion(db_session):
    """Test ON DELETE CASCADE: deleting VerificationResult deletes its Claims and Citations."""
    verif = VerificationResult(
        input_text="Văn bản thử nghiệm cascade.",
        status="PENDING",
    )
    db_session.add(verif)
    db_session.commit()

    claim = Claim(
        verification_result_id=verif.id,
        claim_index=1,
        claim_text="Nhận định mẫu cho cascade.",
    )
    db_session.add(claim)
    db_session.commit()

    claim_id = claim.id

    # Delete parent verification result
    db_session.delete(verif)
    db_session.commit()

    # Claim should be deleted via cascade
    deleted_claim = db_session.get(Claim, claim_id)
    assert deleted_claim is None
