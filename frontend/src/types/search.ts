/**
 * Search and Retrieval schemas matching backend app.schemas.search.
 */

export interface SourceInfo {
  source_id?: string | null;
  title?: string | null;
  url?: string | null;
  publisher?: string | null;
  source_type?: string | null;
}

export interface SearchQueryRequest {
  query: string;
  top_k?: number;
  mode?: 'hybrid' | 'vector' | 'bm25' | string;
  rerank?: boolean;
  score_threshold?: number | null;
  filters?: Record<string, any> | null;
}

export interface SearchHit {
  chunk_id: string;
  document_id?: string | null;
  source_id?: string | null;
  content: string;
  score: number;
  rank?: number | null;
  vector_score?: number | null;
  vector_rank?: number | null;
  bm25_score?: number | null;
  bm25_rank?: number | null;
  rrf_score?: number | null;
  rerank_score?: number | null;
  source?: SourceInfo | Record<string, any> | null;
  source_title?: string | null;
  source_url?: string | null;
  publisher?: string | null;
  page_number?: number | null;
  retriever_type?: 'hybrid' | 'vector' | 'bm25' | 'reranked' | string | null;
  metadata?: Record<string, any> | null;
}

export interface SearchResponse {
  query: string;
  search_type: string;
  total_hits: number;
  rerank_applied?: boolean;
  hits: SearchHit[];
}
