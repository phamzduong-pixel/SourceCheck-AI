/**
 * Document schemas matching backend app.schemas.document.
 *
 * NOTE: Notice the mismatch between upload and ingest:
 * - DocumentUploadResponse uses `document_id`
 * - DocumentResponse uses `id`
 */

export interface DocumentChunkResponse {
  id: string;
  chunk_index: number;
  content: string;
  chunk_metadata?: Record<string, any> | null;
}

export interface DocumentIngestRequest {
  title: string;
  raw_content: string;
  source_url?: string | null;
  publisher?: string | null;
  doc_type?: string;
  metadata?: Record<string, any> | null;
}

export interface DocumentResponse {
  id: string;
  title: string;
  source_url?: string | null;
  publisher?: string | null;
  doc_type: string;
  created_at: string;
  updated_at?: string | null;
  chunk_count: number;
  doc_metadata?: Record<string, any> | null;
}

export interface DocumentDetailResponse extends DocumentResponse {
  raw_content?: string | null;
  chunks: DocumentChunkResponse[];
}

export interface DocumentUploadResponse {
  document_id: string;
  title: string;
  doc_type: string;
  page_count: number;
  total_chunks: number;
  metadata: Record<string, any>;
  chunks: Record<string, any>[];
}

export interface UploadDocumentOptions {
  file: File;
  chunk_strategy?: 'fixed' | 'sentence' | string;
  source_id?: string | null;
}

export interface ListDocumentsParams {
  page?: number;
  page_size?: number;
}
