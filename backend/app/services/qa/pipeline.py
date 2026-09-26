"""End-to-End Q&A Pipeline orchestrating retrieval, reranking, generation, verification, citation, and guardrails."""

import logging
from typing import Any, Dict, List, Optional, Set
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

    async def run(
        self,
        question: str,
        top_k: int = 5,
        search_mode: str = "hybrid",
        session: Optional[AsyncSession] = None,
        metadata: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[str] = None,
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
        if conversation_history and conversation_history.strip():
            rewrite_res = await self.query_rewriter.rewrite(
                question=clean_question,
                history=conversation_history,
            )
            if rewrite_res.is_follow_up and rewrite_res.standalone_query:
                search_query = rewrite_res.standalone_query
                is_follow_up = True
                logger.info(f"Query rewritten for retrieval: '{clean_question}' -> '{search_query}'")

        # 2. Hybrid Retrieval + Reranking (Vector + BM25 + Cross-Encoder)
        fetch_k = top_k * 2
        search_res = await self.retrieval_service.search(
            query=search_query,
            top_k=fetch_k,
            search_mode=search_mode,
            rerank=True,
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

        if gen_res.status == GenerationStatus.INSUFFICIENT_EVIDENCE:
            logger.info("Generation service indicated INSUFFICIENT_EVIDENCE.")
            return AnswerAssembler.create_insufficient_evidence_response(
                question=clean_question,
                reason="generation_insufficient_evidence",
                custom_answer=gen_res.answer,
                metadata={
                    "pipeline_stage": "generation",
                    "model": gen_res.model_name,
                    "search_query": search_query,
                    "is_follow_up": is_follow_up,
                },
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
        )
        candidates_map = matching_resp.claim_matches_map

        # 7. Claim Verification: Evaluate stance (SUPPORTED, PARTIALLY_SUPPORTED, REFUTED, NOT_ENOUGH_INFO)
        verification_results: List[ClaimVerificationResult] = await self.claim_verifier.verify_matches_batch(
            matches=matching_resp.matches
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
        )

        # 11. Final Answer Assembly: Consolidate Answer + Claims + Evidence + Citations + Summary
        meta = metadata or {}
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
                "total_retrieval_hits": search_res.total_hits,
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
        )

        logger.info(
            f"QAPipeline complete for '{clean_question[:40]}...': Status={final_response.status.value}, "
            f"Claims={len(final_response.claims)}, Citations={len(final_response.citations)}"
        )
        return final_response
