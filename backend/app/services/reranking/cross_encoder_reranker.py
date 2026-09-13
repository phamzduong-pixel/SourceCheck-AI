"""Cross-Encoder Reranker implementation with configurable model and resilient fallback."""

import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.schemas.search import SearchHit
from app.services.reranking.base import BaseReranker

logger = logging.getLogger(__name__)


def sigmoid(x: float) -> float:
    """Standard sigmoid function to map logits to (0, 1) range."""
    return 1.0 / (1.0 + math.exp(-max(min(x, 20.0), -20.0)))


class CrossEncoderReranker(BaseReranker):
    """Cross-Encoder Reranker scoring (Query, Candidate Passage) pairs.
    
    Supports real sentence-transformers CrossEncoder neural models,
    with an automatic deterministic cross-scoring fallback for offline/test environments.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        batch_size: int = settings.RERANKER_BATCH_SIZE,
    ):
        super().__init__(model_name=model_name or settings.RERANKER_MODEL)
        self.batch_size = batch_size
        self._model = None
        self._model_loaded = False
        self._init_model()

    def _init_model(self) -> None:
        """Attempt to load neural CrossEncoder model if enabled and available."""
        if settings.RERANKER_PROVIDER == "mock":
            logger.info("RERANKER_PROVIDER='mock'. Using deterministic cross-scoring engine.")
            self._model_loaded = False
            return

        try:
            from sentence_transformers import CrossEncoder

            logger.info(f"Loading CrossEncoder model: {self.model_name}")
            self._model = CrossEncoder(self.model_name)
            self._model_loaded = True
            logger.info("CrossEncoder model loaded successfully.")
        except Exception as e:
            logger.warning(
                f"Could not load neural CrossEncoder ('{self.model_name}'): {e}. "
                "Engaging deterministic fallback cross-scoring engine."
            )
            self._model = None
            self._model_loaded = False

    def _fallback_cross_score(self, query: str, content: str) -> float:
        """Deterministic cross-scoring approximating deep query-passage relevance.
        
        Evaluates:
        1. Exact phrase matching bonus
        2. Query token coverage ratio (Jaccard / intersection)
        3. Term order / bigram preservation
        4. Technical code matching
        """
        if not query or not content:
            return 0.0

        q_clean = query.lower().strip()
        c_clean = content.lower().strip()

        score = 0.0

        # Exact match / consecutive phrase
        if q_clean in c_clean:
            score += 0.50

        # Tokenize words & technical identifiers
        q_tokens = re.findall(r"[\w\d\.\/\%\-]+", q_clean)
        c_tokens = set(re.findall(r"[\w\d\.\/\%\-]+", c_clean))

        if not q_tokens:
            return 0.0

        # Token overlap ratio
        matched_tokens = [t for t in q_tokens if t in c_tokens]
        coverage_ratio = len(matched_tokens) / len(q_tokens)
        score += coverage_ratio * 0.40

        # Bigram coherence
        if len(q_tokens) >= 2:
            q_bigrams = {f"{q_tokens[i]}_{q_tokens[i+1]}" for i in range(len(q_tokens) - 1)}
            c_token_list = re.findall(r"[\w\d\.\/\%\-]+", c_clean)
            c_bigrams = {f"{c_token_list[i]}_{c_token_list[i+1]}" for i in range(len(c_token_list) - 1)}
            bigram_matches = len(q_bigrams.intersection(c_bigrams))
            score += (bigram_matches / len(q_bigrams)) * 0.10

        return round(min(max(score, 0.0), 1.0), 4)

    async def rerank(
        self,
        query: str,
        candidates: List[SearchHit],
        top_k: int = settings.RERANKER_TOP_K,
    ) -> List[SearchHit]:
        """Rerank candidate passages against query and return top_k candidates."""
        if not self.validate_inputs(query, candidates):
            return []

        scored_candidates: List[Tuple[float, SearchHit]] = []

        if self._model_loaded and self._model is not None:
            # Neural CrossEncoder prediction
            try:
                pairs = [[query, hit.content] for hit in candidates]
                raw_scores = self._model.predict(pairs, batch_size=self.batch_size)
                for hit, raw in zip(candidates, raw_scores):
                    val = float(raw)
                    norm_score = sigmoid(val) if val < 0.0 or val > 1.0 else val
                    scored_candidates.append((norm_score, hit))
            except Exception as exc:
                logger.error(f"CrossEncoder inference failed: {exc}. Using fallback.")
                scored_candidates = [
                    (self._fallback_cross_score(query, hit.content), hit)
                    for hit in candidates
                ]
        else:
            # Deterministic fallback engine
            scored_candidates = [
                (self._fallback_cross_score(query, hit.content), hit)
                for hit in candidates
            ]

        # Sort descending by relevance score
        scored_candidates.sort(key=lambda item: item[0], reverse=True)

        # Build output SearchHits
        reranked_hits: List[SearchHit] = []
        for score, original_hit in scored_candidates[:top_k]:
            meta = {
                **(original_hit.metadata or {}),
                "original_retriever_score": original_hit.score,
                "rerank_score": round(score, 4),
                "reranked_by": self.model_name,
                "is_neural": self._model_loaded,
            }
            new_hit = SearchHit(
                chunk_id=original_hit.chunk_id,
                document_id=original_hit.document_id,
                source_id=original_hit.source_id,
                content=original_hit.content,
                score=round(score, 4),
                source=original_hit.source,
                source_title=original_hit.source_title,
                source_url=original_hit.source_url,
                publisher=original_hit.publisher,
                page_number=original_hit.page_number,
                retriever_type="reranked",
                metadata=meta,
            )
            reranked_hits.append(new_hit)

        return reranked_hits
