"""Fact-checking verification endpoints."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from app.schemas.common import APIResponse
from app.schemas.claim import ClaimExtractRequest, ClaimExtractResponse
from app.schemas.verification import (
    VerificationCreateRequest,
    VerificationResultResponse,
)
from app.services.verification.verification_service import VerificationService
from app.services.verification.claim_extractor import ClaimExtractor
from app.api.dependencies import get_verification_service

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
):
    """Run full fact-checking: Extract claims -> Match evidence -> Verify stance -> Detect contradictions."""
    result = await verification_service.verify_text(request)
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
    "/{request_id}",
    response_model=APIResponse[VerificationResultResponse],
    summary="Retrieve past verification report by ID",
)
async def get_verification_report(request_id: uuid.UUID):
    """Retrieve historical verification report by request ID."""
    # Placeholder skeleton
    sample_report = VerificationResultResponse(
        request_id=request_id,
        status="COMPLETED",
        overall_verdict="TRUE",
        summary="Retrieved historical fact-check result.",
        claims_count=1,
        claims=[],
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    return APIResponse(success=True, data=sample_report)
