"""Contradiction detection module: identifies conflicting statements between claims and sources."""

import re
from typing import Any, Dict, List, Optional
from app.schemas.verification import VerifiedClaimItem
from app.services.verification.schemas import (
    ClaimVerificationResult,
    EvidenceConflict,
    MatchedEvidenceCandidate,
    VerificationVerdict,
)


class ContradictionDetector:
    """Analyzes verified claims and evidence sets to flag internal or cross-source contradictions."""

    def __init__(self):
        pass

    def detect_conflicts(
        self,
        verification_results: List[ClaimVerificationResult],
        candidates_map: Optional[Dict[str, List[MatchedEvidenceCandidate]]] = None,
    ) -> List[EvidenceConflict]:
        """Detect direct claim refutations and cross-source evidence disagreements."""
        conflicts: List[EvidenceConflict] = []

        # 1. Claim-level refutations (Evidence directly refutes the claim)
        for res in verification_results:
            if res.verdict == VerificationVerdict.REFUTED and res.refuting_evidence_ids:
                conflicts.append(
                    EvidenceConflict(
                        conflict_type="CLAIM_REFUTATION",
                        claim_id=res.claim_id,
                        claim_text=res.claim_text,
                        evidence_a_id=res.refuting_evidence_ids[0],
                        source_a="Tài liệu đối chiếu",
                        description=f"Nhận định '{res.claim_text}' bị bác bỏ bởi bằng chứng [{res.refuting_evidence_ids[0]}].",
                        severity="HIGH",
                    )
                )

        # 2. Cross-source conflicts (Evidence A vs Evidence B for the same claim)
        if candidates_map:
            claim_text_lookup = {r.claim_id: r.claim_text for r in verification_results}
            negation_words = {"không", "chưa", "chẳng", "not", "never", "no", "sai", "neither", "nor"}

            for claim_id, candidates in candidates_map.items():
                if len(candidates) < 2:
                    continue

                actual_claim_text = claim_text_lookup.get(claim_id, claim_id)

                for i in range(len(candidates)):
                    for j in range(i + 1, len(candidates)):
                        ea = candidates[i]
                        eb = candidates[j]

                        # Check if they come from different sources
                        src_a = ea.source_title or ea.source_id or "Source A"
                        src_b = eb.source_title or eb.source_id or "Source B"

                        # Extract numbers/years (e.g. 2026 vs 2025)
                        nums_a = set(re.findall(r"\b\d+(?:[\.,]\d+)?%?\b", ea.content.lower()))
                        nums_b = set(re.findall(r"\b\d+(?:[\.,]\d+)?%?\b", eb.content.lower()))

                        # Check numerical disagreement
                        if nums_a and nums_b and not nums_a.intersection(nums_b):
                            conflicts.append(
                                EvidenceConflict(
                                    conflict_type="CROSS_SOURCE_CONFLICT",
                                    claim_id=claim_id,
                                    claim_text=actual_claim_text,
                                    evidence_a_id=ea.evidence_id,
                                    evidence_b_id=eb.evidence_id,
                                    source_a=src_a,
                                    source_b=src_b,
                                    description=(
                                        f"Mâu thuẫn dữ liệu giữa hai nguồn: [{ea.evidence_id}] ({src_a}) "
                                        f"và [{eb.evidence_id}] ({src_b}) đưa ra số liệu/năm khác biệt."
                                    ),
                                    severity="HIGH",
                                )
                            )
                            continue

                        # Check negation divergence between sources on the same topic
                        a_has_neg = any(nw in ea.content.lower().split() for nw in negation_words)
                        b_has_neg = any(nw in eb.content.lower().split() for nw in negation_words)
                        if a_has_neg != b_has_neg:
                            conflicts.append(
                                EvidenceConflict(
                                    conflict_type="CROSS_SOURCE_CONFLICT",
                                    claim_id=claim_id,
                                    claim_text=actual_claim_text,
                                    evidence_a_id=ea.evidence_id,
                                    evidence_b_id=eb.evidence_id,
                                    source_a=src_a,
                                    source_b=src_b,
                                    description=(
                                        f"Bất đồng quan điểm giữa hai nguồn: [{ea.evidence_id}] ({src_a}) "
                                        f"và [{eb.evidence_id}] ({src_b}) có khẳng định trái ngược nhau."
                                    ),
                                    severity="HIGH",
                                )
                            )

        return conflicts

    def detect_contradictions(
        self, verified_claims: List[VerifiedClaimItem]
    ) -> List[Dict[str, Any]]:
        """Backward-compatible helper for legacy routers."""
        contradictions = []
        refuted_claims = [c for c in verified_claims if c.verdict == "REFUTED"]
        supported_claims = [c for c in verified_claims if c.verdict == "SUPPORTED"]

        if refuted_claims and supported_claims:
            contradictions.append({
                "type": "MIXED_ACCURACY_CONFLICT",
                "description": "Input text contains a combination of verified facts and refuted claims.",
                "conflicting_claim_ids": [c.claim_id for c in refuted_claims],
            })

        return contradictions
