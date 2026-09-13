"""Pydantic schemas package."""

from app.schemas.common import APIResponse, PaginationParams, PaginatedResponse
from app.schemas.document import (
    DocumentIngestRequest,
    DocumentResponse,
    DocumentDetailResponse,
    DocumentChunkResponse,
)
from app.schemas.search import SearchQueryRequest, SearchHit, SearchResponse
from app.schemas.qa import QuestionRequest, QuestionResponse
from app.schemas.claim import ClaimExtractRequest, ExtractedClaim, ClaimExtractResponse
from app.schemas.verification import (
    VerificationCreateRequest,
    VerificationResultResponse,
    VerifiedClaimItem,
    EvidenceItem,
)
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    TokenPayload,
    GoogleUserInfo,
    GoogleLoginResponse,
)

__all__ = [
    "APIResponse",
    "PaginationParams",
    "PaginatedResponse",
    "DocumentIngestRequest",
    "DocumentResponse",
    "DocumentDetailResponse",
    "DocumentChunkResponse",
    "SearchQueryRequest",
    "SearchHit",
    "SearchResponse",
    "QuestionRequest",
    "QuestionResponse",
    "ClaimExtractRequest",
    "ExtractedClaim",
    "ClaimExtractResponse",
    "VerificationCreateRequest",
    "VerificationResultResponse",
    "VerifiedClaimItem",
    "EvidenceItem",
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "UserResponse",
    "TokenPayload",
    "GoogleUserInfo",
    "GoogleLoginResponse",
]
