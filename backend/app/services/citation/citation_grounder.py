"""Citation grounder extracting exact verbatim quotes from empirical evidence."""

import re
from typing import Any, Dict, Optional
from app.schemas.verification import EvidenceItem


class CitationGrounder:
    """Extracts exact verbatim quote anchors from source evidence passages without hallucination."""

    def extract_verbatim_quote(
        self,
        claim_text: str,
        evidence_content: str,
        max_quote_length: int = 250,
    ) -> str:
        """Extract a verbatim sentence or substring from evidence_content that best matches claim_text.
        
        Guarantees that the returned quote is a strict substring of evidence_content.
        """
        if not evidence_content or not evidence_content.strip():
            return ""

        clean_evidence = evidence_content.strip()
        if len(clean_evidence) <= max_quote_length:
            return clean_evidence

        # Split evidence into candidate sentences
        sentence_regex = re.compile(r"(?<!\d)(?<!\w\.\w)(?<![A-Z][a-z])(?<=[.!?])\s+|\n+")
        sentences = [s.strip() for s in sentence_regex.split(clean_evidence) if s.strip()]

        if not sentences:
            return clean_evidence[:max_quote_length]

        claim_words = set(re.findall(r"\w+", claim_text.lower()))

        best_sentence = sentences[0]
        max_overlap = -1

        for sentence in sentences:
            s_words = set(re.findall(r"\w+", sentence.lower()))
            overlap = len(claim_words.intersection(s_words))
            if overlap > max_overlap:
                max_overlap = overlap
                best_sentence = sentence

        # Verify that best_sentence is a genuine substring of evidence_content
        if best_sentence in clean_evidence:
            if len(best_sentence) > max_quote_length:
                return best_sentence[:max_quote_length]
            return best_sentence

        return clean_evidence[:max_quote_length]

    def find_quote_anchor(self, statement: str, evidence: EvidenceItem) -> Dict[str, Any]:
        """Backward-compatible helper for legacy routers."""
        quote = self.extract_verbatim_quote(statement, evidence.snippet or "")
        return {
            "source_title": evidence.source_title,
            "source_url": evidence.source_url,
            "quote": quote or evidence.snippet[:100],
            "confidence": 0.9,
        }
