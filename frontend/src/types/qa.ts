/**
 * Grounded Q&A schemas matching backend app.schemas.qa and app.services.generation.schemas.
 *
 * NOTE: In this endpoint (/questions/ask), stance and footnote_index are located
 * inside CitationItem, while evidence items contain provenance and chunk info.
 */

import { SourceInfo } from './search';

export type FinalAnswerStatus =
  | 'SUPPORTED'
  | 'PARTIALLY_SUPPORTED'
  | 'REFUTED'
  | 'INSUFFICIENT_EVIDENCE'
  | 'BLOCKED'
  | string;

export type CitationStance = 'SUPPORTS' | 'REFUTES' | 'CONTEXT' | string;
export type QATaskType = 'qa' | 'summary';

export interface QuestionRequest {
  question: string;
  task_type?: QATaskType;
  top_k?: number;
  search_mode?: 'hybrid' | 'vector' | 'bm25' | string;
  /** Whether the composer Search control is enabled. */
  search_enabled?: boolean;
  conversation_id?: string | null;
  /** Optional document scope. Omit to preserve global/backward-compatible Q&A. */
  document_ids?: string[];
}

export interface ClaimItem {
  claim_id: string;
  text: string;
  order: number;
  context_sentence?: string | null;
  verifiable?: boolean;
  verdict?: string | null;
  status?: string | null;
  confidence?: number | null;
  confidence_score?: number | null;
  explanation?: string | null;
  supporting_evidence_ids?: string[];
  refuting_evidence_ids?: string[];
}

export interface QAEvidenceItem {
  evidence_id: string;
  chunk_id: string;
  document_id?: string | null;
  source_id?: string | null;
  content: string;
  score: number;
  source?: SourceInfo | Record<string, any> | null;
  source_title?: string | null;
  source_url?: string | null;
  publisher?: string | null;
  page_number?: number | null;
  metadata?: Record<string, any> | null;
}

export interface CitationItem {
  citation_id: string;
  claim_id: string;
  evidence_id: string;
  chunk_id?: string | null;
  document_id?: string | null;
  source_id?: string | null;
  source_name: string;
  source_url?: string | null;
  quote: string;
  stance: CitationStance;
  footnote_index: number;
  relevance_score: number;
  metadata?: Record<string, any>;
}

export interface SummaryBatchProvenance {
  batch_index: number;
  evidence_ids: string[];
  chunk_ids: string[];
  document_ids: string[];
  page_numbers: Array<number | null>;
  processed: boolean;
  processed_chunk_count: number;
  status: string;
}

export interface AnswerMetadata extends Record<string, any> {
  task_type?: QATaskType;
  document_chunks_total?: number;
  document_chunks_processed?: number;
  document_coverage?: number;
  summary_claim_coverage?: number;
  summary_batch_count?: number;
  summary_successful_batch_count?: number;
  summary_batch_provenance?: SummaryBatchProvenance[];
}

export interface FinalAnswerResponse {
  question: string;
  task_type?: QATaskType;
  answer: string;
  status: FinalAnswerStatus;
  claims: ClaimItem[];
  evidence: QAEvidenceItem[];
  citations: CitationItem[];
  evidence_coverage: number;
  verification_summary: Record<string, number>;
  metadata: AnswerMetadata;
}
