"""Context builder assembling selected evidence into structured context for LLMs."""

import logging
from typing import Dict, List, Optional, Set
from uuid import UUID
from app.schemas.search import SearchHit
from app.services.retrieval.schemas import (
    EvidenceItem,
    SourceInfo,
    StructuredContext,
)

logger = logging.getLogger(__name__)


def estimate_token_count(text: str) -> int:
    """Estimate token count deterministically."""
    if not text:
        return 0
    words = text.split()
    return max(1, max(int(len(words) * 1.3), len(text) // 4))


class ContextBuilder:
    """Formats selected evidence hits into a structured, grounded context block.
    
    Assigns stable identifiers (E1, E2, ...) and preserves full mapping from evidence ID
    to Chunk/Document/Source for downstream Citation and Claim Verification.
    """

    def __init__(
        self,
        max_tokens: int = 3000,
        id_prefix: str = "E",
    ):
        self.max_tokens = max_tokens
        self.id_prefix = id_prefix

    def build_structured_context(
        self,
        query: str,
        evidence_hits: List[SearchHit],
        max_tokens: Optional[int] = None,
        document_ids: Optional[List[UUID]] = None,
    ) -> StructuredContext:
        """Build a StructuredContext object with stable identifiers and mapping.
        
        Args:
            query: User question or claim being verified.
            evidence_hits: Selected, deduplicated SearchHit items.
            max_tokens: Token budget limit.
            
        Returns:
            StructuredContext ready for LLM prompt ingestion.
        """
        token_limit = max_tokens or self.max_tokens

        if not evidence_hits:
            return StructuredContext(
                query=query,
                evidence_items=[],
                context_text="No relevant evidence found.",
                total_evidence=0,
                evidence_map={},
                token_count_estimate=estimate_token_count("No relevant evidence found."),
            )

        if document_ids is not None:
            allowed_document_ids: Set[str] = {str(document_id) for document_id in document_ids}
            out_of_scope_hits = [
                hit for hit in evidence_hits if hit.document_id not in allowed_document_ids
            ]
            if out_of_scope_hits:
                out_of_scope_ids = sorted({hit.document_id for hit in out_of_scope_hits})
                raise ValueError(
                    "Evidence contains document(s) outside the requested scope: "
                    f"{out_of_scope_ids}"
                )

        evidence_items: List[EvidenceItem] = []
        evidence_map: Dict[str, EvidenceItem] = {}
        formatted_blocks: List[str] = []
        accumulated_tokens = 0

        for idx, hit in enumerate(evidence_hits, start=1):
            stable_id = f"{self.id_prefix}{idx}"

            # Ensure source info is populated
            source_info = None
            if hit.source and isinstance(hit.source, dict):
                source_info = SourceInfo(
                    source_id=hit.source.get("id") or hit.source_id,
                    title=hit.source.get("title") or hit.source_title,
                    url=hit.source.get("url") or hit.source_url,
                    publisher=hit.source.get("publisher") or hit.publisher,
                )
            else:
                source_info = SourceInfo(
                    source_id=hit.source_id,
                    title=hit.source_title,
                    url=hit.source_url,
                    publisher=hit.publisher,
                )

            item = EvidenceItem(
                evidence_id=stable_id,
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                source_id=hit.source_id,
                content=hit.content,
                score=hit.score,
                source=source_info,
                source_title=hit.source_title,
                source_url=hit.source_url,
                publisher=hit.publisher,
                page_number=hit.page_number,
                metadata=hit.metadata or {},
            )

            # Format human/LLM-readable text block
            source_desc = hit.source_title or "Tài liệu lưu trữ"
            if hit.source_url:
                source_desc += f" ({hit.source_url})"
            if hit.page_number:
                source_desc += f" [Trang {hit.page_number}]"

            block_text = (
                f"[{stable_id}]\n"
                f"Nguồn: {source_desc}\n"
                f"Độ liên quan: {hit.score:.4f}\n"
                f"Nội dung: \"{hit.content}\""
            )

            block_tokens = estimate_token_count(block_text)

            # Check context token budget
            if accumulated_tokens + block_tokens > token_limit and evidence_items:
                logger.warning(
                    f"Context token budget reached ({accumulated_tokens}/{token_limit}). "
                    f"Truncating at evidence {stable_id}."
                )
                break

            evidence_items.append(item)
            evidence_map[stable_id] = item
            formatted_blocks.append(block_text)
            accumulated_tokens += block_tokens

        full_context_text = "\n\n".join(formatted_blocks)

        return StructuredContext(
            query=query,
            evidence_items=evidence_items,
            context_text=full_context_text,
            total_evidence=len(evidence_items),
            evidence_map=evidence_map,
            token_count_estimate=accumulated_tokens,
        )

    def build_context(self, hits: List[SearchHit]) -> str:
        """Backward-compatible helper returning plain formatted context string."""
        structured = self.build_structured_context(
            query="",
            evidence_hits=hits,
        )
        return structured.context_text
