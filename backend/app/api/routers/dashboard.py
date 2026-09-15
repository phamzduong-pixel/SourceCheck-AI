"""Dashboard and System Overview API Router."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.models.claim import Claim
from app.models.conversation import Conversation
from app.models.document import Document, DocumentChunk
from app.models.evaluation import EvaluationRun
from app.models.qa import Question
from app.models.verification import VerificationResult
from app.schemas.common import APIResponse
from app.schemas.dashboard import (
    DashboardStatsResponse,
    EvaluationSummary,
    RecentActivityItem,
    VerificationDistribution,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/stats",
    response_model=APIResponse[DashboardStatsResponse],
    summary="Retrieve aggregated system metrics and recent activities for the overview dashboard",
)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DashboardStatsResponse]:
    """Aggregate real-time statistics from the database for the dashboard.
    
    Includes counts for documents, chunks, questions, conversations, verifications,
    claims, verification verdict distribution, recent activity timeline, and latest evaluation metrics.
    """
    # 1. Total counts
    total_docs = (await db.scalar(select(func.count(Document.id)))) or 0
    total_chunks = (await db.scalar(select(func.count(DocumentChunk.id)))) or 0
    total_questions = (await db.scalar(select(func.count(Question.id)))) or 0
    total_convs = (await db.scalar(select(func.count(Conversation.id)))) or 0
    total_verifications = (await db.scalar(select(func.count(VerificationResult.id)))) or 0
    total_claims = (await db.scalar(select(func.count(Claim.id)))) or 0

    # 2. Verification distribution
    claim_dist_stmt = select(Claim.verdict, func.count(Claim.id)).group_by(Claim.verdict)
    claim_dist_rows = (await db.execute(claim_dist_stmt)).all()
    claim_map = {row[0]: row[1] for row in claim_dist_rows}

    supported = claim_map.get("SUPPORTED", 0) + claim_map.get("TRUE", 0)
    partially_supported = claim_map.get("PARTIALLY_SUPPORTED", 0) + claim_map.get("MIXED", 0)
    refuted = claim_map.get("REFUTED", 0) + claim_map.get("FALSE", 0)
    not_enough_info = claim_map.get("NOT_ENOUGH_INFO", 0) + claim_map.get("UNVERIFIED", 0)

    # Fallback to verification_results overall_verdict if claims table has 0 rows but verification sessions exist
    if total_claims == 0 and total_verifications > 0:
        v_dist_stmt = select(VerificationResult.overall_verdict, func.count(VerificationResult.id)).group_by(
            VerificationResult.overall_verdict
        )
        v_rows = (await db.execute(v_dist_stmt)).all()
        v_map = {row[0]: row[1] for row in v_rows}
        supported = v_map.get("TRUE", 0) + v_map.get("SUPPORTED", 0)
        partially_supported = v_map.get("MIXED", 0) + v_map.get("PARTIALLY_SUPPORTED", 0)
        refuted = v_map.get("FALSE", 0) + v_map.get("REFUTED", 0)
        not_enough_info = v_map.get("UNVERIFIED", 0) + v_map.get("NOT_ENOUGH_INFO", 0)

    distribution = VerificationDistribution(
        supported=supported,
        partially_supported=partially_supported,
        refuted=refuted,
        not_enough_info=not_enough_info,
    )

    # 3. Recent activity collection
    activities: List[RecentActivityItem] = []

    # Recent documents
    docs_res = await db.execute(select(Document).order_by(Document.created_at.desc()).limit(5))
    for doc in docs_res.scalars().all():
        activities.append(
            RecentActivityItem(
                id=str(doc.id),
                type="document",
                title=f"Tài liệu: {doc.title}",
                description=f"Loại: {doc.doc_type.upper()}",
                status="INGESTED",
                created_at=doc.created_at,
                metadata={"doc_type": doc.doc_type, "source_url": doc.source_url},
            )
        )

    # Recent questions
    q_res = await db.execute(select(Question).order_by(Question.created_at.desc()).limit(5))
    for q in q_res.scalars().all():
        preview = q.question_text[:90] + ("..." if len(q.question_text) > 90 else "")
        activities.append(
            RecentActivityItem(
                id=str(q.id),
                type="question",
                title=f"Hỏi đáp: {preview}",
                description=q.question_text,
                status="ANSWERED",
                created_at=q.created_at,
                metadata={},
            )
        )

    # Recent verifications
    v_res = await db.execute(select(VerificationResult).order_by(VerificationResult.created_at.desc()).limit(5))
    for v in v_res.scalars().all():
        preview = v.input_text[:90] + ("..." if len(v.input_text) > 90 else "")
        activities.append(
            RecentActivityItem(
                id=str(v.id),
                type="verification",
                title=f"Kiểm chứng: {preview}",
                description=v.summary or v.input_text,
                status=v.overall_verdict,
                created_at=v.created_at,
                metadata={
                    "confidence_score": v.confidence_score,
                    "has_contradiction": v.has_contradiction,
                },
            )
        )

    # Recent conversations
    c_res = await db.execute(select(Conversation).order_by(Conversation.created_at.desc()).limit(5))
    for c in c_res.scalars().all():
        activities.append(
            RecentActivityItem(
                id=str(c.id),
                type="conversation",
                title=f"Tra cứu: {c.title}",
                description=c.title,
                status="ACTIVE",
                created_at=c.created_at,
                metadata={"is_pinned": c.is_pinned},
            )
        )

    # Sort all recent activities by created_at descending and take top 10
    activities.sort(key=lambda a: a.created_at, reverse=True)
    recent_activity = activities[:10]

    # 4. Evaluation summary if recorded in DB
    eval_res = await db.execute(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(1))
    latest_eval = eval_res.scalars().first()
    eval_summary: Optional[EvaluationSummary] = None
    if latest_eval:
        eval_summary = EvaluationSummary(
            run_name=latest_eval.run_name,
            dataset_name=latest_eval.dataset_name,
            metrics_summary=latest_eval.metrics_summary,
            created_at=latest_eval.created_at,
        )

    data = DashboardStatsResponse(
        total_documents=total_docs,
        total_chunks=total_chunks,
        total_questions=total_questions,
        total_conversations=total_convs,
        total_verifications=total_verifications,
        total_claims_verified=total_claims,
        verification_distribution=distribution,
        recent_activity=recent_activity,
        evaluation_summary=eval_summary,
    )

    return APIResponse(
        success=True,
        data=data,
        message="Dashboard metrics retrieved successfully.",
    )

