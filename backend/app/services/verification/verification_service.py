"""Verification service orchestrator coordinating the entire fact-checking workflow."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional
from app.schemas.verification import (
    VerificationCreateRequest,
    VerificationResultResponse,
)
from app.services.verification.claim_extractor import ClaimExtractor
from app.services.verification.evidence_matcher import EvidenceMatcher
from app.services.verification.claim_verifier import ClaimVerifier
from app.services.verification.contradiction_detector import ContradictionDetector
from app.services.verification.evidence_coverage import EvidenceCoverageCalculator
from app.services.guardrail.faithfulness import FaithfulnessChecker

if TYPE_CHECKING:
    from app.services.citation.citation_service import CitationService


class VerificationService:
    """Orchestrates end-to-end fact checking pipeline:
    Extract claims -> Match evidence -> Verify stance -> Detect contradictions -> Check faithfulness -> Cite sources.
    """

    def __init__(
        self,
        claim_extractor: Optional[ClaimExtractor] = None,
        evidence_matcher: Optional[EvidenceMatcher] = None,
        claim_verifier: Optional[ClaimVerifier] = None,
        contradiction_detector: Optional[ContradictionDetector] = None,
        coverage_calculator: Optional[EvidenceCoverageCalculator] = None,
        citation_service: Optional["CitationService"] = None,
        faithfulness_checker: Optional[FaithfulnessChecker] = None,
    ):
        self.claim_extractor = claim_extractor or ClaimExtractor()
        self.evidence_matcher = evidence_matcher or EvidenceMatcher()
        self.claim_verifier = claim_verifier or ClaimVerifier()
        self.contradiction_detector = contradiction_detector or ContradictionDetector()
        self.coverage_calculator = coverage_calculator or EvidenceCoverageCalculator()
        if citation_service is None:
            from app.services.citation.citation_service import CitationService as _CitationService
            citation_service = _CitationService()
        self.citation_service = citation_service
        self.faithfulness_checker = faithfulness_checker or FaithfulnessChecker()


    async def verify_text(
        self,
        request: VerificationCreateRequest,
        session: Optional[Any] = None,
    ) -> VerificationResultResponse:
        """Run full verification pipeline."""
        req_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # 1. Extract factual claims
        claims = await self.claim_extractor.extract_claims(request.text)

        # 2. Match evidence for each claim (hybrid search + cross-encoder rerank)
        matched_evidence = await self.evidence_matcher.match_evidence_for_claims(
            claims, top_k=request.top_k_evidence, session=session
        )

        # 3. Verify each claim with matched evidence
        verified_claims = []
        all_evidences = []
        for claim in claims:
            claim_key = claim.claim_id or claim.claim_text
            evidence_hits = matched_evidence.get(claim_key, [])
            verified_claim = await self.claim_verifier.verify_claim(claim, evidence_hits)
            verified_claims.append(verified_claim)
            all_evidences.extend(verified_claim.evidences)

        # 4. Check contradictions if enabled
        if request.enable_contradiction_check:
            self.contradiction_detector.detect_contradictions(verified_claims)

        # 5. Check faithfulness / hallucination mitigation
        if all_evidences:
            self.faithfulness_checker.check_faithfulness(request.text, all_evidences)

        # 6. Determine overall verdict & calculate evidence coverage
        supported_count = sum(1 for c in verified_claims if c.verdict in ("SUPPORTED", "PARTIALLY_SUPPORTED"))
        refuted_count = sum(1 for c in verified_claims if c.verdict == "REFUTED")
        nei_count = sum(1 for c in verified_claims if c.verdict == "NOT_ENOUGH_INFO")

        if not verified_claims or nei_count == len(verified_claims):
            overall = "UNVERIFIED"
        elif supported_count > 0 and refuted_count == 0:
            overall = "TRUE" if supported_count == len(verified_claims) else "SUPPORTED"
        elif refuted_count > 0 and supported_count == 0:
            overall = "FALSE"
        else:
            overall = "MIXED"

        coverage_metrics = self.coverage_calculator.calculate_coverage(verified_claims)
        cov_pct = int(coverage_metrics.get("coverage_rate", 0.0) * 100)

        summary_text = (
            f"Processed {len(verified_claims)} claim(s): "
            f"{supported_count} SUPPORTED, {refuted_count} REFUTED, {nei_count} NOT_ENOUGH_INFO. "
            f"Evidence Coverage: {cov_pct}%. Verdict: {overall}."
        )

        # 7. Format inline citations / references
        if all_evidences:
            summary_text = self.citation_service.format_inline_citations(
                summary_text, all_evidences
            )

        return VerificationResultResponse(
            request_id=req_id,
            status="COMPLETED",
            overall_verdict=overall,
            summary=summary_text,
            claims_count=len(verified_claims),
            claims=verified_claims,
            created_at=now,
            completed_at=datetime.now(timezone.utc),
        )

    async def verify_structured_answer(
        self,
        answer: str,
        context: Optional[Any] = None,
        top_k_evidence: int = 3,
    ) -> Any:
        """Execute end-to-end claim extraction, evidence matching, and verification on an answer."""
        from app.services.verification.schemas import VerificationReport

        # 1. Extract atomic claims from answer
        extraction_resp = await self.claim_extractor.extract(answer=answer)
        claims = extraction_resp.claims

        if not claims:
            return VerificationReport(
                total_claims=0,
                verified_claims_count=0,
                evidence_coverage=0.0,
                average_confidence=0.0,
                results=[],
                conflicts=[],
                has_contradictions=False,
                metadata={"reason": "no_claims_extracted"},
            )

        # 2. Match claims against context evidence items if provided
        evidence_items = getattr(context, "evidence_items", []) if context else []
        matching_resp = await self.evidence_matcher.match_claims_to_evidence(
            claims=claims,
            evidence_items=evidence_items,
            top_k=top_k_evidence,
        )

        # 3. Verify each claim match
        results = await self.claim_verifier.verify_matches_batch(matching_resp.matches)

        # 4. Detect contradictions and cross-source conflicts
        conflicts = self.contradiction_detector.detect_conflicts(
            verification_results=results,
            candidates_map=matching_resp.claim_matches_map,
        )

        # 5. Compute quantitative evidence coverage
        metrics = self.coverage_calculator.compute_coverage(results)

        return VerificationReport(
            total_claims=metrics["total_claims"],
            verified_claims_count=metrics["verified_claims"],
            evidence_coverage=metrics["coverage_rate"],
            average_confidence=metrics["average_confidence"],
            results=results,
            conflicts=conflicts,
            has_contradictions=len(conflicts) > 0,
            metadata={
                "extraction_mode": extraction_resp.extraction_mode,
                "total_matched_evidences": matching_resp.total_matches,
            },
        )

