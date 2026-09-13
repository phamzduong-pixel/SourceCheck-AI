"""Verification package: Domain-specific fact-checking components for SourceCheck AI."""

from app.services.verification.base import BaseClaimExtractor
from app.services.verification.claim_extractor import (
    ClaimExtractor,
    LLMClaimExtractor,
    RuleBasedClaimExtractor,
)
from app.services.verification.claim_verifier import ClaimVerifier
from app.services.verification.contradiction_detector import ContradictionDetector
from app.services.verification.evidence_coverage import EvidenceCoverageCalculator
from app.services.verification.evidence_matcher import EvidenceMatcher
from app.services.verification.schemas import (
    ClaimEvidenceMatch,
    ClaimExtractionOutput,
    ClaimExtractionResponse,
    ClaimItem,
    ClaimVerificationResult,
    EvidenceConflict,
    EvidenceMatchingResponse,
    EvidenceRelation,
    MatchedEvidenceCandidate,
    VerificationReport,
    VerificationVerdict,
)
from app.services.verification.verification_service import VerificationService

__all__ = [
    "BaseClaimExtractor",
    "ClaimExtractor",
    "LLMClaimExtractor",
    "RuleBasedClaimExtractor",
    "ClaimItem",
    "ClaimExtractionOutput",
    "ClaimExtractionResponse",
    "EvidenceRelation",
    "MatchedEvidenceCandidate",
    "ClaimEvidenceMatch",
    "EvidenceMatchingResponse",
    "EvidenceMatcher",
    "ClaimVerifier",
    "VerificationVerdict",
    "ClaimVerificationResult",
    "EvidenceConflict",
    "VerificationReport",
    "ContradictionDetector",
    "EvidenceCoverageCalculator",
    "VerificationService",
]
