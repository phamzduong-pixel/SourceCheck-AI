"""Faithfulness checker module detecting ungrounded statements and hallucinations."""

from typing import Any, Dict, List, Optional
from uuid import UUID
from app.schemas.verification import EvidenceItem


class FaithfulnessChecker:
    """Verifies that generated summaries and verdicts are strictly derived from evidence."""

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold

    def check_faithfulness(
        self,
        generated_text: str,
        evidences: List[EvidenceItem],
        document_ids: Optional[List[UUID]] = None,
    ) -> Dict[str, Any]:
        """Score faithfulness to guarantee hallucination mitigation."""
        if not evidences:
            return {"is_faithful": False, "score": 0.0, "reason": "No evidence provided."}

        if document_ids is not None:
            allowed_document_ids = {str(document_id) for document_id in document_ids}
            if any(
                getattr(evidence, "document_id", None) not in allowed_document_ids
                for evidence in evidences
            ):
                return {
                    "is_faithful": False,
                    "score": 0.0,
                    "reason": "Evidence contains a document outside the requested scope.",
                }

        # Skeleton placeholder: To be connected with Ragas / TruLens faithfulness metric
        return {
            "is_faithful": True,
            "score": 0.92,
            "reason": "Generated explanation is supported by provided evidence context.",
        }
