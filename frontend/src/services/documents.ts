/**
 * Document Ingestion and Management service.
 * Endpoints: /api/v1/documents/*
 */

import { apiClient } from './apiClient';
import {
  DocumentDetailResponse,
  DocumentIngestRequest,
  DocumentResponse,
  DocumentUploadResponse,
  ListDocumentsParams,
  UploadDocumentOptions,
} from '../types/document';
import { PaginatedResponse } from '../types/common';

export const documentService = {
  /**
   * Retrieve paginated list of ingested documents.
   * Endpoint: GET /api/v1/documents
   */
  async listDocuments(params?: ListDocumentsParams): Promise<PaginatedResponse<DocumentResponse>> {
    return apiClient.get<PaginatedResponse<DocumentResponse>>('/documents', {
      params: {
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 20,
      },
    });
  },

  /**
   * Upload and ingest a physical document (PDF, TXT, DOCX).
   * Endpoint: POST /api/v1/documents/upload
   *
   * Note: Backend returns DocumentUploadResponse containing `document_id`.
   */
  async uploadDocument(options: UploadDocumentOptions): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', options.file);

    if (options.chunk_strategy) {
      formData.append('chunk_strategy', options.chunk_strategy);
    }

    if (options.source_id) {
      formData.append('source_id', options.source_id);
    }

    return apiClient.upload<DocumentUploadResponse>('/documents/upload', formData);
  },

  /**
   * Ingest raw text content into the knowledge store.
   * Endpoint: POST /api/v1/documents/ingest
   *
   * Note: Backend returns DocumentResponse containing `id`.
   */
  async ingestDocument(request: DocumentIngestRequest): Promise<DocumentResponse> {
    return apiClient.post<DocumentResponse>('/documents/ingest', request);
  },

  /**
   * Retrieve document metadata and chunks by document ID.
   * Endpoint: GET /api/v1/documents/{document_id}
   */
  async getDocument(documentId: string): Promise<DocumentDetailResponse> {
    return apiClient.get<DocumentDetailResponse>(`/documents/${documentId}`);
  },

  /**
   * Permanently delete a document and its associated chunks.
   * Endpoint: DELETE /api/v1/documents/{document_id}
   */
  async deleteDocument(documentId: string): Promise<{ document_id: string; title: string }> {
    return apiClient.delete<{ document_id: string; title: string }>(`/documents/${documentId}`);
  },
};
