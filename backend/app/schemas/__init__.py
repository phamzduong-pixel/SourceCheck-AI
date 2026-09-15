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
from app.schemas.conversation import (
    MessageRole,
    MessageCreate,
    MessageRead,
    ConversationCreate,
    ConversationRead,
    ConversationSummary,
)

from app.schemas.dashboard import (
    VerificationDistribution,
    RecentActivityItem,
    EvaluationSummary,
    DashboardStatsResponse,
)
from app.schemas.health import (
    DependencyHealth,
    SystemHealthResponse,
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
    "MessageRole",
    "MessageCreate",
    "MessageRead",
    "ConversationCreate",
    "ConversationRead",
    "ConversationSummary",
    "VerificationDistribution",
    "RecentActivityItem",
    "EvaluationSummary",
    "DashboardStatsResponse",
    "DependencyHealth",
    "SystemHealthResponse",
]

