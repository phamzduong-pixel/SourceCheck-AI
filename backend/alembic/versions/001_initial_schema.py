"""Initial schema with pgvector extension and 11 core tables.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-13 22:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector
from pgvector.sqlalchemy import Vector
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Table: users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)

    # 3. Table: sources
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="news"),
        sa.Column("reliability_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_sources_domain", "sources", ["domain"], unique=True)

    # 4. Table: documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("doc_type", sa.String(length=50), nullable=False, server_default="text"),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("doc_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_documents_source_id", "documents", ["source_id"])

    # 5. Table: document_chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(settings.EMBEDDING_DIM), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_document_chunks_document_id", "document_chunks", ["document_id"])
    # HNSW Index for vector cosine similarity
    op.execute(
        "CREATE INDEX idx_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 100);"
    )

    # 6. Table: questions
    op.create_table(
        "questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_questions_user_id", "questions", ["user_id"])

    # 7. Table: answers
    op.create_table(
        "answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questions.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 8. Table: verification_results
    op.create_table(
        "verification_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("overall_verdict", sa.String(length=50), nullable=False, server_default="UNVERIFIED"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("has_contradiction", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_verification_results_user_created", "verification_results", ["user_id", "created_at"])

    # 9. Table: claims
    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("verification_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("verification_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("verdict", sa.String(length=50), nullable=False, server_default="NOT_ENOUGH_INFO"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_claims_verification_result_id", "claims", ["verification_result_id"])

    # 10. Table: evidences
    op.create_table(
        "evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("source_title", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_evidences_chunk_id", "evidences", ["document_chunk_id"])
    op.create_index("idx_evidences_source_id", "evidences", ["source_id"])

    # 11. Table: citations
    op.create_table(
        "citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=True),
        sa.Column("answer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("answers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stance", sa.String(length=50), nullable=False, server_default="NEUTRAL"),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("citation_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("(claim_id IS NOT NULL) OR (answer_id IS NOT NULL)", name="check_citation_target_not_null"),
    )
    op.create_index("idx_citations_claim_id", "citations", ["claim_id"])
    op.create_index("idx_citations_answer_id", "citations", ["answer_id"])
    op.create_index("idx_citations_evidence_id", "citations", ["evidence_id"])

    # 12. Table: evaluation_runs
    op.create_table(
        "evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_name", sa.String(length=255), nullable=False),
        sa.Column("dataset_name", sa.String(length=100), nullable=False),
        sa.Column("model_config", postgresql.JSONB(), nullable=True),
        sa.Column("metrics_summary", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evaluation_runs")
    op.drop_table("citations")
    op.drop_table("evidences")
    op.drop_table("claims")
    op.drop_table("verification_results")
    op.drop_table("answers")
    op.drop_table("questions")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("sources")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector CASCADE;")
