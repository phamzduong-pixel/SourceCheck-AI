"""End-to-End Q&A Pipeline orchestrating retrieval, reranking, generation, verification, citation, and guardrails."""

import logging
from typing import Any, Dict, List, Optional, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.citation.citation_service import CitationService
from app.services.generation.answer_assembler import AnswerAssembler
from app.services.generation.generation_service import GenerationService
from app.services.generation.schemas import (
    FinalAnswerResponse,
    FinalAnswerStatus,
    GenerationStatus,
)
from app.services.guardrail.guardrail_service import GuardrailService
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.verification.claim_extractor import ClaimExtractor
from app.services.verification.claim_verifier import ClaimVerifier
from app.services.verification.contradiction_detector import ContradictionDetector
from app.services.verification.evidence_coverage import EvidenceCoverageCalculator
from app.services.verification.evidence_matcher import EvidenceMatcher
from app.services.verification.schemas import (
    ClaimItem,
    ClaimVerificationResult,
    VerificationReport,
    VerificationVerdict,
)
from app.services.qa.intent_router import IntentRouter
from app.services.qa.query_rewriter import QueryRewriter
from app.services.qa.document_summary import DocumentSummaryService

logger = logging.getLogger(__name__)


class QAPipeline:
    """Deterministic, grounded Question Answering pipeline with multi-stage verification and guardrails."""

    def __init__(
        self,
        retrieval_service: Optional[RetrievalService] = None,
        generation_service: Optional[GenerationService] = None,
        claim_extractor: Optional[ClaimExtractor] = None,
        evidence_matcher: Optional[EvidenceMatcher] = None,
        claim_verifier: Optional[ClaimVerifier] = None,
        contradiction_detector: Optional[ContradictionDetector] = None,
        coverage_calculator: Optional[EvidenceCoverageCalculator] = None,
        citation_service: Optional[CitationService] = None,
        guardrail_service: Optional[GuardrailService] = None,
        query_rewriter: Optional[QueryRewriter] = None,
        intent_router: Optional[IntentRouter] = None,
        summary_service: Optional[DocumentSummaryService] = None,
    ):
        self.retrieval_service = retrieval_service or RetrievalService()
        self.generation_service = generation_service or GenerationService()
        self.claim_extractor = claim_extractor or ClaimExtractor()
        self.evidence_matcher = evidence_matcher or EvidenceMatcher()
        self.claim_verifier = claim_verifier or ClaimVerifier()
        self.contradiction_detector = contradiction_detector or ContradictionDetector()
        self.coverage_calculator = coverage_calculator or EvidenceCoverageCalculator()
        self.citation_service = citation_service or CitationService()
        self.guardrail_service = guardrail_service or GuardrailService()
        self.query_rewriter = query_rewriter or QueryRewriter()
        self.intent_router = intent_router or IntentRouter()
        self.summary_service = summary_service or DocumentSummaryService(generation_service=self.generation_service)

    @staticmethod
    def _enforce_summary_verification_scope(
        verification_results: List[ClaimVerificationResult],
        candidates_map,
        structured_context,
        document_ids: List[UUID],
    ) -> List[ClaimVerificationResult]:
        """Ensure summary verdicts only rely on matched evidence in the selected document."""
        allowed_documents = {str(document_id) for document_id in document_ids}
        valid_context_ids = set(structured_context.evidence_map.keys())
        sanitized_results: List[ClaimVerificationResult] = []

        for result in verification_results:
            candidates = candidates_map.get(result.claim_id, [])
            valid_candidate_ids = {
                candidate.evidence_id
                for candidate in candidates
                if candidate.evidence_id in valid_context_ids
                and candidate.document_id in allowed_documents
            }
            supporting_ids = [
                evidence_id
                for evidence_id in result.supporting_evidence_ids
                if evidence_id in valid_candidate_ids
            ]
            refuting_ids = [
                evidence_id
                for evidence_id in result.refuting_evidence_ids
                if evidence_id in valid_candidate_ids
            ]

            has_valid_evidence = (
                bool(supporting_ids)
                if result.verdict in (
                    VerificationVerdict.SUPPORTED,
                    VerificationVerdict.PARTIALLY_SUPPORTED,
                )
                else bool(refuting_ids)
                if result.verdict == VerificationVerdict.REFUTED
                else False
            )

            if result.verdict != VerificationVerdict.NOT_ENOUGH_INFO and not has_valid_evidence:
                sanitized_results.append(
                    result.model_copy(
                        update={
                            "verdict": VerificationVerdict.NOT_ENOUGH_INFO,
                            "confidence": 0.0,
                            "supporting_evidence_ids": [],
                            "refuting_evidence_ids": [],
                            "explanation": (
                                "Summary claim was downgraded because no valid evidence "
                                "from the selected document was available."
                            ),
                        }
                    )
                )
                continue

            sanitized_results.append(
                result.model_copy(
                    update={
                        "supporting_evidence_ids": supporting_ids,
                        "refuting_evidence_ids": refuting_ids,
                    }
                )
            )

        return sanitized_results

    @staticmethod
    def _summary_claim_coverage(
        results: List[ClaimVerificationResult],
    ) -> float:
        """Measure summary claims with a valid evidence-backed verdict."""
        if not results:
            return 0.0
        covered = sum(
            1
            for result in results
            if result.verdict != VerificationVerdict.NOT_ENOUGH_INFO
            and (result.supporting_evidence_ids or result.refuting_evidence_ids)
        )
        return round(covered / len(results), 4)

    async def run(
        self,
        question: str,
        top_k: int = 5,
        search_mode: str = "hybrid",
        search_enabled: bool = True,
        session: Optional[AsyncSession] = None,
        metadata: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[str] = None,
        document_ids: Optional[List[UUID]] = None,
        task_type: str = "qa",
    ) -> FinalAnswerResponse:
        """Execute the 13-stage deterministic Q&A pipeline.
        
        Order:
        Question -> Input Guardrail -> Contextual Query Rewrite -> Hybrid Search ->
        Reranking -> Evidence Selection -> Context Builder -> LLM Generation ->
        Claim Extraction -> Evidence Matching -> Claim Verification ->
        Contradiction Detection -> Citation Service -> Answer Assembler ->
        Output Guardrail -> Final Answer
        """
        logger.info(f"Starting QAPipeline for query: '{question[:80]}...'")

        # 1. Input Guardrail: Validate query safety & format
        input_audit = self.guardrail_service.validate_input(question)
        if not input_audit.is_valid:
            logger.warning(f"Input Guardrail rejected query: {input_audit.flagged_reasons}")
            return AnswerAssembler.create_blocked_response(
                question=question or "",
                reasons=input_audit.flagged_reasons,
                metadata={"pipeline_stage": "input_guardrail"},
            )

        clean_question = input_audit.sanitized_input

        # 1.2 Intent Router: Deterministic greeting / identity / smalltalk handling
        intent_result = self.intent_router.route(clean_question)
        if intent_result.is_matched and intent_result.canned_response:
            logger.info(
                f"Intent Router matched '{intent_result.intent}' (sub={intent_result.sub_intent}) for query: '{clean_question[:40]}'"
            )
            meta = metadata.copy() if metadata else {}
            meta.update(
                {
                    "sub_intent": intent_result.sub_intent,
                    "intent_type": intent_result.intent.value if intent_result.intent else None,
                }
            )
            return AnswerAssembler.create_canned_response(
                question=clean_question,
                answer=intent_result.canned_response,
                intent=intent_result.intent.value if intent_result.intent else "GREETING",
                metadata=meta,
            )

        search_query = clean_question
        is_follow_up = False

        # 1.5 Contextual Query Reformulation for follow-up queries
        # Search OFF preserves grounded retrieval but skips contextual query rewriting.
        if search_enabled and conversation_history and conversation_history.strip():
            rewrite_res = await self.query_rewriter.rewrite(
                question=clean_question,
                history=conversation_history,
            )
            if rewrite_res.is_follow_up and rewrite_res.standalone_query:
                search_query = rewrite_res.standalone_query
                is_follow_up = True
                logger.info(f"Query rewritten for retrieval: '{clean_question}' -> '{search_query}'")

        normalized_task_type = (
            task_type.value if hasattr(task_type, "value") else str(task_type)
        ).lower()
        summary_metadata: Dict[str, Any] = {}
        search_total_hits = 0

        if normalized_task_type == "summary":
            if not document_ids or len(document_ids) != 1:
                raise ValueError("Summary requires exactly one document_id.")

            summary_result = await self.summary_service.summarize(
                question=clean_question,
                document_id=document_ids[0],
                session=session,
            )
            structured_context = summary_result.verification_context
            gen_res = summary_result.generation
            search_query = clean_question
            search_total_hits = summary_result.document_chunks_total
            summary_metadata = {
                "document_chunks_total": summary_result.document_chunks_total,
                "document_chunks_processed": summary_result.document_chunks_processed,
                "document_coverage": summary_result.document_coverage,
                "summary_batch_count": summary_result.batch_count,
                "summary_successful_batch_count": summary_result.successful_batch_count,
                "summary_batch_provenance": summary_result.batch_provenance,
            }
        else:
            # 2. Hybrid Retrieval + Reranking (Vector + BM25 + Cross-Encoder)
            fetch_k = top_k * 2
            search_res = await self.retrieval_service.search(
                query=search_query,
                top_k=fetch_k,
                search_mode=search_mode,
                rerank=True,
                filters={"document_ids": document_ids} if document_ids is not None else None,
                session=session,
            )

            if not search_res.hits:
                logger.info("No retrieval hits found. Returning INSUFFICIENT_EVIDENCE.")
                return AnswerAssembler.create_insufficient_evidence_response(
                    question=clean_question,
                    reason="no_retrieval_hits",
                    metadata={
                        "pipeline_stage": "retrieval",
                        "total_hits": 0,
                        "search_query": search_query,
                        "is_follow_up": is_follow_up,
                    },
                )

            # 3. Evidence Selection & Structured Context Assembly
            structured_context = self.retrieval_service.build_evidence_context(
                hits=search_res.hits,
                query=search_query,
                max_evidence=top_k,
                document_ids=document_ids,
            )

            if structured_context.total_evidence == 0 or not structured_context.evidence_items:
                logger.info("No evidence remaining after selection. Returning INSUFFICIENT_EVIDENCE.")
                return AnswerAssembler.create_insufficient_evidence_response(
                    question=clean_question,
                    reason="no_valid_evidence_after_selection",
                    metadata={
                        "pipeline_stage": "evidence_selection",
                        "search_query": search_query,
                        "is_follow_up": is_follow_up,
                    },
                )

            # 4. LLM Generation: Grounded answer synthesis
            gen_res = await self.generation_service.generate_answer(
                question=clean_question,
                context=structured_context,
                conversation_history=conversation_history,
            )
            search_total_hits = search_res.total_hits

        if gen_res.status == GenerationStatus.INSUFFICIENT_EVIDENCE:
            logger.info("Generation service indicated INSUFFICIENT_EVIDENCE.")
            insufficient_metadata = {
                "pipeline_stage": "generation",
                "model": gen_res.model_name,
                "search_query": search_query,
                "is_follow_up": is_follow_up,
            }
            if normalized_task_type == "summary":
                insufficient_metadata.update(
                    {
                        "task_type": normalized_task_type,
                        **summary_metadata,
                        "summary_claim_coverage": 0.0,
                    }
                )
            return AnswerAssembler.create_insufficient_evidence_response(
                question=clean_question,
                reason="generation_insufficient_evidence",
                custom_answer=gen_res.answer,
                metadata=insufficient_metadata,
            )

        # 5. Claim Extraction: Decompose answer into verifiable claims
        claim_resp = await self.claim_extractor.extract(
            answer=gen_res.answer,
            context=structured_context.context_text,
        )
        claims: List[ClaimItem] = claim_resp.claims
        if not claims:
            claims = [
                ClaimItem(
                    claim_id="claim_1",
                    text=gen_res.answer.strip(),
                    order=1,
                    verifiable=True,
                )
            ]

        # 6. Evidence Matching: Match claims against context candidates
        matching_resp = await self.evidence_matcher.match_context_claims(
            claims=claims,
            context=structured_context,
            document_ids=document_ids,
        )
        candidates_map = matching_resp.claim_matches_map

        # 7. Claim Verification: Evaluate stance (SUPPORTED, PARTIALLY_SUPPORTED, REFUTED, NOT_ENOUGH_INFO)
        verification_results: List[ClaimVerificationResult] = await self.claim_verifier.verify_matches_batch(
            matches=matching_resp.matches,
            document_ids=document_ids,
        )
        if normalized_task_type == "summary":
            verification_results = self._enforce_summary_verification_scope(
                verification_results=verification_results,
                candidates_map=candidates_map,
                structured_context=structured_context,
                document_ids=document_ids or [],
            )

        # 8. Contradiction Detection: Check claim refutations & cross-source conflicts
        conflicts = self.contradiction_detector.detect_conflicts(
            verification_results=verification_results,
            candidates_map=candidates_map,
        )

        # 9. Evidence Coverage & Verification Summary Report
        cov_metrics = self.coverage_calculator.compute_coverage(results=verification_results)
        verification_report = VerificationReport(
            total_claims=len(claims),
            verified_claims_count=cov_metrics["verified_claims"],
            evidence_coverage=cov_metrics["coverage_rate"],
            average_confidence=cov_metrics["average_confidence"],
            results=verification_results,
            conflicts=conflicts,
            has_contradictions=len(conflicts) > 0,
        )

        # 10. Citation Service: Verbatim quotes, stable footnote indexing [1], [2], deduplication
        citation_summary = self.citation_service.build_citations(
            verification_results=verification_results,
            candidates_map=candidates_map,
            document_ids=document_ids,
        )

        # 11. Final Answer Assembly: Consolidate Answer + Claims + Evidence + Citations + Summary
        meta = metadata or {}
        if normalized_task_type == "summary":
            summary_metadata["summary_claim_coverage"] = self._summary_claim_coverage(
                verification_results
            )
        meta.update(
            {
                "conflicts": [c.model_dump() for c in conflicts],
                "_claim_verdicts": {
                    result.claim_id: {
                        "verdict": result.verdict.value,
                        "confidence_score": result.confidence,
                        "explanation": result.explanation,
                    }
                    for result in verification_results
                },
                "footnotes_text": citation_summary.footnotes_text,
                "token_estimate": structured_context.token_count_estimate,
                "total_retrieval_hits": search_total_hits,
                "task_type": normalized_task_type,
                **summary_metadata,
                "search_query": search_query,
                "is_follow_up": is_follow_up,
            }
        )

        assembled = AnswerAssembler.assemble(
            question=clean_question,
            answer=gen_res.answer,
            claims=claims,
            evidence=structured_context.evidence_items,
            verification_report=verification_report,
            citations=citation_summary.citations,
            metadata=meta,
        )

        # 12. Final Output Guardrail: Check claim completeness, citation integrity, and grounding rules
        valid_evidence_ids: Set[str] = set(structured_context.evidence_map.keys())
        final_response = self.guardrail_service.apply_final_guardrail(
            response=assembled,
            valid_evidence_ids=valid_evidence_ids,
            verification_results=verification_results,
            document_ids=document_ids,
        )

        logger.info(
            f"QAPipeline complete for '{clean_question[:40]}...': Status={final_response.status.value}, "
            f"Claims={len(final_response.claims)}, Citations={len(final_response.citations)}"
        )
        return final_response
