"""Output Guardrail service validating final answer, claim completeness, citation grounding, and schema integrity."""

import logging
from typing import List, Optional, Set
from uuid import UUID
from app.services.generation.schemas import FinalAnswerResponse, FinalAnswerStatus
from app.services.guardrail.schemas import GuardrailStatus, OutputValidationResult

from app.services.verification.schemas import ClaimVerificationResult, VerificationVerdict

logger = logging.getLogger(__name__)


class OutputGuardrail:
    """Validates the assembled final answer response to guarantee correctness and safety."""

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def validate_response(
        self,
        response: FinalAnswerResponse,
        valid_evidence_ids: Optional[Set[str]] = None,
        verification_results: Optional[List[ClaimVerificationResult]] = None,
        document_ids: Optional[List[UUID]] = None,
    ) -> OutputValidationResult:
        """Thoroughly audit the final answer response against grounding, claim, citation, and status policies.
        
        Args:
            response: The assembled FinalAnswerResponse to validate.
            valid_evidence_ids: Set of genuine evidence IDs (e.g. {'E1', 'E2'}) from retrieved context.
            verification_results: List of actual ClaimVerificationResult records.
            
        Returns:
            OutputValidationResult with validity flag, status, and list of violations.
        """
        violations: List[str] = []
        allowed_document_ids: Optional[Set[str]] = (
            None if document_ids is None else {str(document_id) for document_id in document_ids}
        )
        if allowed_document_ids is not None:
            for evidence in response.evidence:
                if evidence.document_id not in allowed_document_ids:
                    violations.append(
                        f"Evidence '{evidence.evidence_id}' belongs to document '{evidence.document_id}', outside the requested scope."
                    )
            for citation in response.citations:
                if citation.document_id not in allowed_document_ids:
                    violations.append(
                        f"Citation '{citation.citation_id}' belongs to document '{citation.document_id}', outside the requested scope."
                    )

        valid_eids = valid_evidence_ids or set()
        if not valid_eids and response.evidence:
            valid_eids = {e.evidence_id for e in response.evidence if getattr(e, "evidence_id", None)}

        # 1. If response was already marked INSUFFICIENT_EVIDENCE or BLOCKED, verify it has no fake citations/claims
        if response.status in (FinalAnswerStatus.INSUFFICIENT_EVIDENCE, FinalAnswerStatus.BLOCKED):
            if response.citations:
                violations.append(
                    f"Response status is {response.status.value} but contains {len(response.citations)} unexpected citations."
                )
            return OutputValidationResult(
                is_valid=len(violations) == 0,
                status=GuardrailStatus.PASSED if not violations else GuardrailStatus.BLOCKED,
                violations=violations,
                metadata={"status": response.status.value},
            )

        # 2. Check claim verification completeness:
        # Every claim in response.claims must have a corresponding verification result
        if response.claims:
            verified_claim_ids = set()
            if verification_results is not None:
                verified_claim_ids = {r.claim_id for r in verification_results}
            elif response.metadata.get("verified_claim_ids"):
                verified_claim_ids = set(response.metadata["verified_claim_ids"])
            else:
                # If no explicit list provided, check if verification_summary accounts for all claims
                total_in_summary = sum(response.verification_summary.values())
                if total_in_summary < len(response.claims):
                    violations.append(
                        f"Unverified claims detected: total claims ({len(response.claims)}) exceeds verified count in summary ({total_in_summary})."
                    )

            if verification_results is not None or response.metadata.get("verified_claim_ids"):
                for claim in response.claims:
                    if claim.claim_id not in verified_claim_ids:
                        violations.append(
                            f"Claim '{claim.claim_id}' has no corresponding verification result."
                        )


        # 3. Check citation-to-evidence integrity:
        # Every citation MUST point to an existing, genuine evidence item
        is_summary_response = response.metadata.get("task_type") == "summary"
        if response.citations:
            evidence_by_id = {evidence.evidence_id: evidence for evidence in response.evidence}
            for cit in response.citations:
                # Check evidence_id exists
                if valid_eids and cit.evidence_id not in valid_eids:
                    violations.append(
                        f"Citation '{cit.citation_id}' references non-existent evidence ID '{cit.evidence_id}'."
                    )
                # Check for fabricated / empty quote
                if not cit.quote or not cit.quote.strip():
                    violations.append(
                        f"Citation '{cit.citation_id}' has an empty or missing quote."
                    )
                # Check for empty source name
                if not cit.source_name or not cit.source_name.strip():
                    violations.append(
                        f"Citation '{cit.citation_id}' is missing a valid source name."
                    )
                cited_evidence = evidence_by_id.get(cit.evidence_id)
                if is_summary_response and cited_evidence is not None:
                    if cit.document_id != cited_evidence.document_id:
                        violations.append(
                            f"Citation '{cit.citation_id}' document does not match its evidence item."
                        )
                    if cit.chunk_id != cited_evidence.chunk_id:
                        violations.append(
                            f"Citation '{cit.citation_id}' chunk does not match its evidence item."
                        )
                    citation_page = cit.metadata.get("page_number") if cit.metadata else None
                    if citation_page != cited_evidence.page_number:
                        violations.append(
                            f"Citation '{cit.citation_id}' page does not match its evidence item."
                        )

        # Summary outputs must expose a citation for every claim that received
        # an evidence-backed positive or partial verdict.
        if response.metadata.get("task_type") == "summary" and verification_results is not None:
            cited_claim_ids = {citation.claim_id for citation in response.citations}
            for result in verification_results:
                if result.verdict in (
                    VerificationVerdict.SUPPORTED,
                    VerificationVerdict.PARTIALLY_SUPPORTED,
                ) and result.claim_id not in cited_claim_ids:
                    violations.append(
                        f"Summary claim '{result.claim_id}' has an evidence-backed verdict but no citation."
                    )

        # 4. Check for ungrounded / unsupported status claim:
        # If response claims SUPPORTED, it must have at least one SUPPORTED claim and evidence
        summary = response.verification_summary
        if response.status == FinalAnswerStatus.SUPPORTED:
            if summary.get("SUPPORTED", 0) == 0:
                violations.append(
                    "Response status claims SUPPORTED, but verification summary contains zero SUPPORTED claims."
                )
            if not response.evidence:
                violations.append(
                    "Response status claims SUPPORTED, but contains zero backing evidence items."
                )

        # 5. Determine guardrail outcome
        if violations:
            logger.warning(f"OutputGuardrail detected violations: {violations}")
            return OutputValidationResult(
                is_valid=False,
                status=GuardrailStatus.BLOCKED,
                violations=violations,
                metadata={"violation_count": len(violations)},
            )

        return OutputValidationResult(
            is_valid=True,
            status=GuardrailStatus.PASSED,
            violations=[],
            metadata={"status": response.status.value},
        )
