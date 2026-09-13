"""Citation service orchestrator linking verified claims and evidence to structured citations."""

import logging
import uuid
from typing import Dict, List, Optional
from app.schemas.verification import EvidenceItem as LegacyEvidenceItem
from app.services.citation.citation_formatter import CitationFormatter
from app.services.citation.citation_grounder import CitationGrounder
from app.services.citation.schemas import (
    CitationItem,
    CitationStance,
    CitationSummary,
)
from app.services.verification.schemas import (
    ClaimVerificationResult,
    MatchedEvidenceCandidate,
    VerificationVerdict,
)

logger = logging.getLogger(__name__)


class CitationService:
    """Creates deterministic citations linking verified claims to underlying empirical evidence."""

    def __init__(
        self,
        grounder: Optional[CitationGrounder] = None,
        formatter: Optional[CitationFormatter] = None,
    ):
        self.grounder = grounder or CitationGrounder()
        self.formatter = formatter or CitationFormatter()

    def build_citations(
        self,
        verification_results: List[ClaimVerificationResult],
        candidates_map: Dict[str, List[MatchedEvidenceCandidate]],
    ) -> CitationSummary:
        """Construct structured citations for verification results.
        
        Args:
            verification_results: List of verified claims with verdicts and evidence IDs.
            candidates_map: Lookup map from claim_id to list of candidate MatchedEvidenceCandidates.
            
        Returns:
            CitationSummary containing structured citations, unique evidence count, and formatted references.
        """
        citations: List[CitationItem] = []

        # Mapping to guarantee stable, sequential 1-indexed footnote numbers across distinct evidences
        evidence_footnote_map: Dict[str, int] = {}
        current_footnote_index = 1

        for res in verification_results:
            candidates = candidates_map.get(res.claim_id, [])
            candidates_by_eid = {c.evidence_id: c for c in candidates}

            # Gather cited evidence IDs based on verdict
            active_evidence_ids = []
            if res.verdict == VerificationVerdict.SUPPORTED or res.verdict == VerificationVerdict.PARTIALLY_SUPPORTED:
                active_evidence_ids = res.supporting_evidence_ids or [c.evidence_id for c in candidates[:1]]
                stance = CitationStance.SUPPORTS
            elif res.verdict == VerificationVerdict.REFUTED:
                active_evidence_ids = res.refuting_evidence_ids or [c.evidence_id for c in candidates[:1]]
                stance = CitationStance.REFUTES
            else:
                # NOT_ENOUGH_INFO or unverified
                active_evidence_ids = [c.evidence_id for c in candidates[:1]] if candidates else []
                stance = CitationStance.CONTEXT

            for eid in active_evidence_ids:
                cand = candidates_by_eid.get(eid)
                if not cand:
                    continue

                # Deduplicate footnote indices across identical evidence passages (by chunk_id or evidence_id)
                evidence_key = cand.chunk_id or cand.evidence_id
                if evidence_key not in evidence_footnote_map:
                    evidence_footnote_map[evidence_key] = current_footnote_index
                    current_footnote_index += 1

                f_idx = evidence_footnote_map[evidence_key]

                # Extract verbatim quote directly from evidence snippet
                verbatim_quote = self.grounder.extract_verbatim_quote(
                    claim_text=res.claim_text,
                    evidence_content=cand.content,
                )

                source_name = cand.source_title or "Tài liệu kiểm chứng"

                citations.append(
                    CitationItem(
                        citation_id=f"cite_{uuid.uuid4().hex[:8]}",
                        claim_id=res.claim_id,
                        evidence_id=cand.evidence_id,
                        chunk_id=cand.chunk_id,
                        document_id=cand.document_id,
                        source_id=cand.source_id,
                        source_name=source_name,
                        source_url=cand.source_url,
                        quote=verbatim_quote,
                        stance=stance,
                        footnote_index=f_idx,
                        relevance_score=cand.relevance_score,
                        metadata={
                            "page_number": cand.page_number,
                            "publisher": cand.publisher,
                        },
                    )
                )

        # Build formatted reference lines and markdown footnote section
        formatted_references = [self.formatter.format_entry(c) for c in citations]
        footnotes_text = self.formatter.format_footnotes_section(citations)

        return CitationSummary(
            total_citations=len(citations),
            unique_evidence_count=len(evidence_footnote_map),
            citations=citations,
            formatted_references=formatted_references,
            footnotes_text=footnotes_text,
            metadata={"distinct_footnotes": len(evidence_footnote_map)},
        )

    def format_inline_citations(
        self, text: str, evidences: List[LegacyEvidenceItem]
    ) -> str:
        """Backward-compatible helper for legacy routers."""
        if not evidences:
            return text

        references = ["\n\n### References:"]
        for idx, ev in enumerate(evidences, 1):
            ref_entry = f"[{idx}] {ev.source_title}"
            if ev.source_url:
                ref_entry += f" - {ev.source_url}"
            references.append(ref_entry)

        return text + "\n".join(references)
