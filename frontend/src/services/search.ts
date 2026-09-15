/**
 * Search and Retrieval service.
 * Endpoints: /api/v1/search/*
 */

import { apiClient } from './apiClient';
import { SearchQueryRequest, SearchResponse } from '../types/search';

export const searchService = {
  /**
   * Execute unified search supporting mode=hybrid|vector|bm25 and optional Cross-Encoder reranking.
   * Endpoint: POST /api/v1/search?mode=...&rerank=...
   */
  async search(
    request: SearchQueryRequest,
    mode?: 'hybrid' | 'vector' | 'bm25' | string,
    rerank?: boolean
  ): Promise<SearchResponse> {
    return apiClient.post<SearchResponse>('/search', request, {
      params: {
        mode: mode || request.mode || undefined,
        rerank: rerank !== undefined ? rerank : request.rerank,
      },
    });
  },

  /**
   * Execute Hybrid (Dense Vector + Sparse BM25 via RRF) search with optional reranking.
   * Endpoint: POST /api/v1/search/hybrid
   */
  async hybridSearch(request: SearchQueryRequest, rerank?: boolean): Promise<SearchResponse> {
    return apiClient.post<SearchResponse>('/search/hybrid', request, {
      params: rerank !== undefined ? { rerank } : undefined,
    });
  },

  /**
   * Execute pure Vector similarity search with pgvector.
   * Endpoint: POST /api/v1/search/vector
   */
  async vectorSearch(request: SearchQueryRequest): Promise<SearchResponse> {
    return apiClient.post<SearchResponse>('/search/vector', request);
  },

  /**
   * Execute pure BM25 Lexical search for exact terms and entities.
   * Endpoint: POST /api/v1/search/bm25
   */
  async bm25Search(request: SearchQueryRequest): Promise<SearchResponse> {
    return apiClient.post<SearchResponse>('/search/bm25', request);
  },
};
