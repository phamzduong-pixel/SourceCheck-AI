"""Search endpoints for Vector, BM25, and Hybrid retrieval."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db, get_retrieval_service
from app.core.exceptions import SourceCheckException
from app.schemas.common import APIResponse
from app.schemas.search import SearchQueryRequest, SearchResponse
from app.services.retrieval.retrieval_service import RetrievalService

router = APIRouter(prefix="/search", tags=["Search"])


@router.post(
    "",
    response_model=APIResponse[SearchResponse],
    summary="Unified Search endpoint supporting mode=hybrid|vector|bm25 with optional Cross-Encoder reranking",
)
async def search_endpoint(
    request: SearchQueryRequest,
    mode: str = Query(default=None, description="Search mode: hybrid, vector, or bm25"),
    rerank: bool = Query(default=None, description="Apply Cross-Encoder reranking"),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve relevant passages using requested search mode (defaults to hybrid) and optional reranking."""
    try:
        selected_mode = mode or request.mode or "hybrid"
        should_rerank = rerank if rerank is not None else (request.rerank or False)
        response = await retrieval_service.search(
            query=request.query,
            top_k=request.top_k,
            search_mode=selected_mode,
            score_threshold=request.score_threshold,
            rerank=should_rerank,
            filters=request.filters,
            session=db,
        )
        return APIResponse(success=True, data=response)
    except SourceCheckException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message, "details": e.details},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/hybrid",
    response_model=APIResponse[SearchResponse],
    summary="Execute Hybrid (Dense Vector + Sparse BM25 via RRF) search with optional Cross-Encoder reranking",
)
async def hybrid_search(
    request: SearchQueryRequest,
    rerank: bool = Query(default=None, description="Apply Cross-Encoder reranking"),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve relevant passages using hybrid search with Reciprocal Rank Fusion."""
    try:
        should_rerank = rerank if rerank is not None else (request.rerank or False)
        response = await retrieval_service.search(
            query=request.query,
            top_k=request.top_k,
            search_mode="hybrid",
            score_threshold=request.score_threshold,
            rerank=should_rerank,
            filters=request.filters,
            session=db,
        )
        return APIResponse(success=True, data=response)
    except SourceCheckException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message, "details": e.details},
        )


@router.post(
    "/vector",
    response_model=APIResponse[SearchResponse],
    summary="Execute pure Vector similarity search with pgvector",
)
async def vector_search(
    request: SearchQueryRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve relevant passages using dense vector embeddings in PostgreSQL."""
    try:
        should_rerank = request.rerank or False
        response = await retrieval_service.search(
            query=request.query,
            top_k=request.top_k,
            search_mode="vector",
            score_threshold=request.score_threshold,
            rerank=should_rerank,
            filters=request.filters,
            session=db,
        )
        return APIResponse(success=True, data=response)
    except SourceCheckException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message, "details": e.details},
        )


@router.post(
    "/bm25",
    response_model=APIResponse[SearchResponse],
    summary="Execute pure BM25 Lexical search for exact terms and entities",
)
async def bm25_search(
    request: SearchQueryRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve relevant passages using sparse BM25 keyword matching."""
    try:
        should_rerank = request.rerank or False
        response = await retrieval_service.search(
            query=request.query,
            top_k=request.top_k,
            search_mode="bm25",
            rerank=should_rerank,
            filters=request.filters,
            session=db,
        )
        return APIResponse(success=True, data=response)
    except SourceCheckException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message, "details": e.details},
        )
