"""Document-wide, evidence-grounded summary orchestration."""

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.document_repository import DocumentRepository
from app.services.generation.generation_service import GenerationService
from app.services.generation.schemas import GenerationResponse, GenerationStatus
from app.services.retrieval.context_builder import estimate_token_count
from app.services.retrieval.schemas import EvidenceItem, SourceInfo, StructuredContext

logger = logging.getLogger(__name__)


@dataclass
class DocumentSummaryResult:
    """Generated summary plus the complete source evidence used downstream."""

    generation: GenerationResponse
    verification_context: StructuredContext
    document_chunks_total: int
    document_chunks_processed: int
    document_coverage: float
    batch_count: int
    successful_batch_count: int
    batch_provenance: List[Dict[str, Any]] = field(default_factory=list)


class DocumentSummaryService:
    """Loads one document's ordered chunks and summarizes them in bounded batches."""

    DEFAULT_CONTEXT_TOKEN_BUDGET = 3000

    def __init__(
        self,
        repository: Optional[DocumentRepository] = None,
        generation_service: Optional[GenerationService] = None,
        context_token_budget: int = DEFAULT_CONTEXT_TOKEN_BUDGET,
    ):
        self.repository = repository
        self.generation_service = generation_service or GenerationService()
        self.context_token_budget = context_token_budget

    @staticmethod
    def _page_number(chunk) -> int:
        metadata = chunk.chunk_metadata if isinstance(chunk.chunk_metadata, dict) else {}
        value = metadata.get("page_number")
        return int(value) if isinstance(value, int) else 0

    @classmethod
    def _ordered_chunks(cls, document):
        return sorted(
            document.chunks or [],
            key=lambda chunk: (cls._page_number(chunk), chunk.chunk_index, str(chunk.id)),
        )

    @staticmethod
    def _source_publisher(document) -> Optional[str]:
        metadata = document.doc_metadata if isinstance(document.doc_metadata, dict) else {}
        return metadata.get("publisher")

    @classmethod
    def _to_evidence_items(cls, document) -> List[EvidenceItem]:
        publisher = cls._source_publisher(document)
        source_info = SourceInfo(
            source_id=str(document.source_id) if document.source_id else None,
            title=document.title,
            url=document.source_url,
            publisher=publisher,
        )
        items: List[EvidenceItem] = []
        for index, chunk in enumerate(cls._ordered_chunks(document), start=1):
            items.append(
                EvidenceItem(
                    evidence_id=f"E{index}",
                    chunk_id=str(chunk.id),
                    document_id=str(document.id),
                    source_id=str(document.source_id) if document.source_id else None,
                    content=chunk.content,
                    score=1.0,
                    source=source_info,
                    source_title=document.title,
                    source_url=document.source_url,
                    publisher=publisher,
                    page_number=cls._page_number(chunk) or None,
                    metadata=dict(chunk.chunk_metadata or {}),
                )
            )
        return items

    @staticmethod
    def _format_evidence(item: EvidenceItem) -> str:
        page = f" [Page {item.page_number}]" if item.page_number else ""
        return (
            f"[{item.evidence_id}]\n"
            f"Source: {item.source_title or 'Selected document'}{page}\n"
            f'Content: "{item.content}"'
        )

    def _build_batches(
        self,
        question: str,
        evidence_items: List[EvidenceItem],
    ) -> List[StructuredContext]:
        batches: List[List[EvidenceItem]] = []
        current: List[EvidenceItem] = []
        current_tokens = 0

        for item in evidence_items:
            block = self._format_evidence(item)
            block_tokens = estimate_token_count(block)
            if current and current_tokens + block_tokens > self.context_token_budget:
                batches.append(current)
                current = []
                current_tokens = 0

            current.append(item)
            current_tokens += block_tokens

        if current:
            batches.append(current)

        return [
            StructuredContext(
                query=question,
                evidence_items=batch,
                context_text="\n\n".join(self._format_evidence(item) for item in batch),
                total_evidence=len(batch),
                evidence_map={item.evidence_id: item for item in batch},
                token_count_estimate=sum(
                    estimate_token_count(self._format_evidence(item)) for item in batch
                ),
            )
            for batch in batches
        ]

    async def summarize(
        self,
        question: str,
        document_id: UUID,
        session: Optional[AsyncSession] = None,
    ) -> DocumentSummaryResult:
        repository = self.repository or DocumentRepository(session)
        document = await repository.get_with_chunks(document_id)
        if document is None:
            raise ValueError(f"Document '{document_id}' was not found.")

        evidence_items = self._to_evidence_items(document)
        batches = self._build_batches(question, evidence_items)
        partial_answers: List[str] = []
        generated_evidence_ids: List[str] = []
        successful_batches = 0
        processed_chunk_count = 0
        batch_provenance: List[Dict[str, Any]] = []

        for batch_index, batch in enumerate(batches, start=1):
            batch_evidence_ids = [item.evidence_id for item in batch.evidence_items]
            batch_chunk_ids = [item.chunk_id for item in batch.evidence_items]
            batch_pages = [item.page_number for item in batch.evidence_items]
            generated = await self.generation_service.generate_summary(
                question=question,
                context=batch,
            )
            valid_generated_ids = [
                evidence_id
                for evidence_id in generated.evidence_ids
                if evidence_id in batch.evidence_map
            ]
            batch_succeeded = bool(
                generated.status == GenerationStatus.SUPPORTED
                and generated.answer.strip()
                and valid_generated_ids
            )
            for item in batch.evidence_items:
                item.metadata = {
                    **(item.metadata or {}),
                    "summary_batch_index": batch_index,
                    "summary_batch_processed": batch_succeeded,
                }

            batch_provenance.append(
                {
                    "batch_index": batch_index,
                    "evidence_ids": batch_evidence_ids,
                    "chunk_ids": batch_chunk_ids,
                    "document_ids": sorted({item.document_id for item in batch.evidence_items}),
                    "page_numbers": batch_pages,
                    "processed": batch_succeeded,
                    "processed_chunk_count": len(batch.evidence_items) if batch_succeeded else 0,
                    "status": generated.status.value,
                }
            )

            if batch_succeeded:
                partial_answers.append(generated.answer.strip())
                successful_batches += 1
                processed_chunk_count += len(batch.evidence_items)
                generated_evidence_ids.extend(valid_generated_ids)
            else:
                logger.warning("Summary batch %s did not produce a supported answer.", batch_index)

        if partial_answers:
            answer = "\n\n".join(partial_answers)
            generation = GenerationResponse(
                question=question,
                answer=answer,
                status=GenerationStatus.SUPPORTED,
                evidence_ids=list(dict.fromkeys(generated_evidence_ids)),
                metadata={
                    "summary_batch_count": len(batches),
                    "summary_successful_batch_count": successful_batches,
                    "summary_batch_provenance": batch_provenance,
                },
            )
        else:
            generation = GenerationResponse(
                question=question,
                answer="The selected document does not contain enough evidence to produce a grounded summary.",
                status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                evidence_ids=[],
                metadata={
                    "summary_batch_count": len(batches),
                    "summary_successful_batch_count": 0,
                    "summary_batch_provenance": batch_provenance,
                },
            )

        verification_context = StructuredContext(
            query=question,
            evidence_items=evidence_items,
            context_text="\n\n".join(self._format_evidence(item) for item in evidence_items),
            total_evidence=len(evidence_items),
            evidence_map={item.evidence_id: item for item in evidence_items},
            token_count_estimate=sum(
                estimate_token_count(self._format_evidence(item)) for item in evidence_items
            ),
        )
        total_chunks = len(evidence_items)
        return DocumentSummaryResult(
            generation=generation,
            verification_context=verification_context,
            document_chunks_total=total_chunks,
            document_chunks_processed=processed_chunk_count,
            document_coverage=(
                round(processed_chunk_count / total_chunks, 4) if total_chunks else 0.0
            ),
            batch_count=len(batches),
            successful_batch_count=successful_batches,
            batch_provenance=batch_provenance,
        )