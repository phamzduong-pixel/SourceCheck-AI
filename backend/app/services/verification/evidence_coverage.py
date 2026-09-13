"""Evidence coverage calculator: assesses completeness and reliability of supporting evidence."""

from typing import Dict, List, Union
from app.schemas.verification import VerifiedClaimItem
from app.services.verification.schemas import (
    ClaimVerificationResult,
    VerificationVerdict,
)


class EvidenceCoverageCalculator:
    """Calculates quantitative metrics for evidence support across all claims.
    
    Evidence Coverage = verified claims (SUPPORTED, PARTIALLY_SUPPORTED, REFUTED) / total verifiable claims.
    NOTE: This metric measures evidence completeness, NOT answer accuracy.
    """

    def compute_coverage(
        self,
        results: List[ClaimVerificationResult],
    ) -> Dict[str, float]:
        """Compute coverage percentage, confidence average, and verified claims count."""
        if not results:
            return {
                "coverage_rate": 0.0,
                "average_confidence": 0.0,
                "total_claims": 0,
                "verified_claims": 0,
            }

        total = len(results)
        # Claims that received an informative verdict based on evidence
        verified = sum(
            1
            for r in results
            if r.verdict in [
                VerificationVerdict.SUPPORTED,
                VerificationVerdict.PARTIALLY_SUPPORTED,
                VerificationVerdict.REFUTED,
            ]
        )

        avg_confidence = sum(r.confidence for r in results) / total if total > 0 else 0.0

        return {
            "coverage_rate": round(verified / total, 4),
            "average_confidence": round(avg_confidence, 4),
            "total_claims": total,
            "verified_claims": verified,
        }

    def calculate_coverage(
        self, verified_claims: List[Union[VerifiedClaimItem, ClaimVerificationResult]]
    ) -> Dict[str, float]:
        """Backward-compatible helper for legacy routers."""
        if not verified_claims:
            return {"coverage_rate": 0.0, "average_confidence": 0.0, "claims_with_evidence": 0.0}

        total = len(verified_claims)
        with_evidence = 0
        conf_sum = 0.0

        for c in verified_claims:
            if isinstance(c, ClaimVerificationResult):
                if c.verdict != VerificationVerdict.NOT_ENOUGH_INFO:
                    with_evidence += 1
                conf_sum += c.confidence
            else:
                if len(c.evidences) > 0:
                    with_evidence += 1
                conf_sum += c.confidence_score

        return {
            "coverage_rate": round(with_evidence / total, 2),
            "average_confidence": round(conf_sum / total, 2),
            "total_claims": total,
            "claims_with_evidence": with_evidence,
        }
