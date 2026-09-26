"""Fact-checking verification endpoints."""

import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.schemas.common import APIResponse
from app.schemas.claim import ClaimExtractRequest, ClaimExtractResponse
from app.schemas.verification import (
    EvidenceItem,
    VerificationCreateRequest,
    VerificationHistoryItem,
    VerificationHistoryResponse,
    VerificationResultResponse,
    VerifiedClaimItem,
)
from app.models.claim import Claim
from app.models.citation import Citation
from app.models.verification import VerificationResult
from app.models.user import User
from app.repositories.verification_repository import VerificationRepository
from app.services.verification.verification_service import VerificationService
from app.services.verification.claim_extractor import ClaimExtractor
from app.api.dependencies import get_verification_service, get_db, get_current_active_user

router = APIRouter(prefix="/verify", tags=["Verification"])


@router.post(
    "",
    response_model=APIResponse[VerificationResultResponse],
    status_code=status.HTTP_200_OK,
    summary="Execute full verification pipeline for text or article",
)
async def verify_content(
    request: VerificationCreateRequest,
    verification_service: VerificationService = Depends(get_verification_service),
    db: AsyncSession = Depends(get_db),
):
    """Run full fact-checking: Extract claims -> Match evidence -> Verify stance -> Detect contradictions."""
    result = await verification_service.verify_text(request, session=db)
    return APIResponse(
        success=True,
        data=result,
        message=f"Verification completed with verdict: {result.overall_verdict}",
    )


@router.post(
    "/extract-claims",
    response_model=APIResponse[ClaimExtractResponse],
    summary="Extract atomic verifiable claims from input text",
)
async def extract_claims(request: ClaimExtractRequest):
    """Extract verifiable claims without running full verification."""
    extractor = ClaimExtractor()
    claims = await extractor.extract_claims(request.text, max_claims=request.max_claims)
    return APIResponse(
        success=True,
        data=ClaimExtractResponse(total_claims=len(claims), claims=claims),
    )


@router.get(
    "/history",
    response_model=APIResponse[VerificationHistoryResponse],
    summary="List recent verification results for the current user",
)
async def get_verification_history(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    records = await VerificationRepository(db).get_user_history(
        user_id=current_user.id, skip=skip, limit=limit
    )
    items = [
        VerificationHistoryItem(
            request_id=record.id,
            question=record.input_text,
            answer_preview=(record.summary or "")[:240] or None,
            overall_verdict=record.overall_verdict,
            status=record.status,
            evidence_coverage=record.confidence_score,
            created_at=record.created_at,
        )
        for record in records
    ]
    return APIResponse(
        success=True,
        data=VerificationHistoryResponse(items=items, skip=skip, limit=limit),
    )

@router.get(
    "/{request_id}",
    response_model=APIResponse[VerificationResultResponse],
    summary="Retrieve past verification report by ID",
)
async def get_verification_report(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve historical verification report from database by request ID."""
    stmt = (
        select(VerificationResult)
        .where(VerificationResult.id == request_id)
        .options(
            selectinload(VerificationResult.claims)
            .selectinload(Claim.citations)
            .selectinload(Citation.evidence)
        )
    )
    result = await db.execute(stmt)
    verif_rec = result.scalar_one_or_none()

    if verif_rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy báo cáo kiểm chứng với mã ID: {request_id}",
        )

    claims_list: List[VerifiedClaimItem] = []
    for cl in sorted(verif_rec.claims, key=lambda x: x.claim_index):
        evidence_items: List[EvidenceItem] = []
        for cit in sorted(cl.citations, key=lambda c: c.citation_number):
            ev = cit.evidence
            if ev:
                evidence_items.append(
                    EvidenceItem(
                        evidence_id=str(ev.id),
                        source_title=ev.source_title,
                        source_url=ev.source_url,
                        publisher=ev.publisher,
                        snippet=ev.snippet,
                        stance=cit.stance,
                        quote=cit.quote,
                        relevance_score=cit.relevance_score,
                    )
                )
        claims_list.append(
            VerifiedClaimItem(
                claim_id=str(cl.id),
                claim_text=cl.claim_text,
                verdict=cl.verdict,
                confidence_score=cl.confidence_score,
                explanation=cl.explanation,
                evidences=evidence_items,
            )
        )

    report_data = VerificationResultResponse(
        request_id=verif_rec.id,
        status=verif_rec.status,
        overall_verdict=verif_rec.overall_verdict,
        summary=verif_rec.summary,
        claims_count=len(claims_list),
        claims=claims_list,
        created_at=verif_rec.created_at,
        completed_at=verif_rec.completed_at or verif_rec.created_at,
    )

    return APIResponse(
        success=True,
        data=report_data,
        message=f"Báo cáo kiểm chứng được tải thành công với kết quả: {verif_rec.overall_verdict}",
    )
