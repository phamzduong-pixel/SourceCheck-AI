/**
 * Unit & Integration Tests for Centralized API Client & Service Functions.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiClient, ApiClientError } from '../services/apiClient';
import { TOKEN_STORAGE_KEY } from '../services/auth';
import { qaService } from '../services/qa';
import { verificationService } from '../services/verification';
import { documentService } from '../services/documents';
import { searchService } from '../services/search';
import { systemService } from '../services/system';
import conversationService from '../services/conversations';

describe('Centralized API Client & Services', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  describe('1. Authentication Token Injection', () => {
    it('automatically attaches Authorization: Bearer <token> when token is present', async () => {
      localStorage.setItem(TOKEN_STORAGE_KEY, 'test-jwt-token-123');

      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: { status: 'ok' } }),
      } as Response);

      await apiClient.get('/test-endpoint');

      expect(fetchSpy).toHaveBeenCalledTimes(1);
      const callHeaders = fetchSpy.mock.calls[0][1]?.headers as Headers;
      expect(callHeaders.get('Authorization')).toBe('Bearer test-jwt-token-123');
    });

    it('does not send Authorization header when token is not in storage', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: { status: 'public' } }),
      } as Response);

      await apiClient.get('/public-endpoint');

      expect(fetchSpy).toHaveBeenCalledTimes(1);
      const callHeaders = fetchSpy.mock.calls[0][1]?.headers as Headers;
      expect(callHeaders.get('Authorization')).toBeNull();
    });

    it('omits Authorization header when skipAuth is true even if token exists', async () => {
      localStorage.setItem(TOKEN_STORAGE_KEY, 'test-jwt-token-123');

      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ status: 'healthy', service: 'SourceCheck AI', environment: 'test' }),
      } as Response);

      await apiClient.get('/health', { rawPath: true, skipAuth: true });

      expect(fetchSpy).toHaveBeenCalledTimes(1);
      const callHeaders = fetchSpy.mock.calls[0][1]?.headers as Headers;
      expect(callHeaders.get('Authorization')).toBeNull();
    });
  });

  describe('Conversations authentication', () => {
    it('calls the canonical conversations endpoint with the stored Bearer token', async () => {
      localStorage.setItem(TOKEN_STORAGE_KEY, 'conversation-jwt-token');
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: [] }),
      } as Response);

      await conversationService.listConversations();

      expect(String(fetchSpy.mock.calls[0][0])).toBe('/api/v1/conversations/');
      const headers = fetchSpy.mock.calls[0][1]?.headers as Headers;
      expect(headers.get('Authorization')).toBe('Bearer conversation-jwt-token');
    });
  });

  describe('2. Error Handling & Payload Preservation', () => {
    it('parses FastAPI validation error array without losing message', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: false,
        status: 422,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          detail: [
            { loc: ['body', 'question'], msg: 'Field required', type: 'missing' },
          ],
        }),
      } as Response);

      try {
        await apiClient.post('/questions/ask', {});
        expect.unreachable('Should have thrown an ApiClientError');
      } catch (err: any) {
        expect(err).toBeInstanceOf(ApiClientError);
        expect(err.statusCode).toBe(422);
        expect(err.message).toContain('Field required');
      }
    });

    it('parses custom APIResponse error envelope', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          success: false,
          data: null,
          message: 'Tài liệu không hợp lệ hoặc quá hạn mức.',
          error: { code: 'DOC_LIMIT_EXCEEDED' },
        }),
      } as Response);

      await expect(apiClient.post('/documents/ingest', {})).rejects.toThrow(
        'Tài liệu không hợp lệ hoặc quá hạn mức.'
      );
    });

    it('handles HTTP 401 with appropriate message', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => null,
      } as Response);

      try {
        await apiClient.get('/auth/me');
      } catch (err: any) {
        expect(err).toBeInstanceOf(ApiClientError);
        expect(err.statusCode).toBe(401);
        expect(err.message).toContain('401');
      }
    });

    it('handles network failure gracefully', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Failed to fetch'));

      try {
        await apiClient.get('/test-network');
      } catch (err: any) {
        expect(err).toBeInstanceOf(ApiClientError);
        expect(err.statusCode).toBe(0);
        expect(err.message).toContain('Không thể kết nối');
      }
    });
  });

  describe('3. HTTP Methods & Multipart Uploads', () => {
    it('appends query params accurately to GET requests', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: { total: 0, items: [] } }),
      } as Response);

      await apiClient.get('/items', { params: { page: 1, limit: 10, active: true } });

      const targetUrl = String(fetchSpy.mock.calls[0][0]);
      expect(targetUrl).toContain('/items?page=1&limit=10&active=true');
    });

    it('handles rawPath parameter without prepending API base url', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ status: 'healthy' }),
      } as Response);

      await apiClient.get('/health', { rawPath: true });

      const targetUrl = String(fetchSpy.mock.calls[0][0]);
      expect(targetUrl).toBe('/health');
    });

    it('uploads FormData without overriding multipart Content-Type header', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 201,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          success: true,
          data: {
            document_id: 'doc-123',
            title: 'test.pdf',
            doc_type: 'pdf',
            page_count: 5,
            total_chunks: 10,
            metadata: {},
            chunks: [],
          },
        }),
      } as Response);

      const formData = new FormData();
      formData.append('file', new Blob(['test content'], { type: 'text/plain' }), 'test.txt');

      await apiClient.upload('/documents/upload', formData);

      expect(fetchSpy).toHaveBeenCalledTimes(1);
      const callHeaders = fetchSpy.mock.calls[0][1]?.headers as Headers;
      // Content-Type should NOT be application/json for multipart upload
      expect(callHeaders.get('Content-Type')).toBeNull();
    });
  });

  describe('4. Domain Service Functions Contract', () => {
    it('qaService.askQuestion calls /questions/ask and unwraps FinalAnswerResponse', async () => {
      const mockAnswer = {
        question: 'Việt Nam gia nhập WTO năm nào?',
        answer: 'Việt Nam chính thức gia nhập WTO vào năm 2007 [1].',
        status: 'SUPPORTED',
        claims: [
          { claim_id: 'c1', text: 'Việt Nam gia nhập WTO năm 2007', order: 1, verifiable: true },
        ],
        evidence: [
          {
            evidence_id: 'E1',
            chunk_id: 'ch-1',
            content: 'Năm 2007, Việt Nam trở thành thành viên chính thức của WTO.',
            score: 0.95,
          },
        ],
        citations: [
          {
            citation_id: 'cit-1',
            claim_id: 'c1',
            evidence_id: 'E1',
            source_name: 'Bộ Công Thương',
            quote: 'Năm 2007, Việt Nam trở thành thành viên...',
            stance: 'SUPPORTS',
            footnote_index: 1,
            relevance_score: 0.95,
          },
        ],
        evidence_coverage: 1.0,
        verification_summary: { SUPPORTED: 1, REFUTED: 0, PARTIALLY_SUPPORTED: 0, NOT_ENOUGH_INFO: 0 },
        metadata: {},
      };

      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: mockAnswer }),
      } as Response);

      const result = await qaService.askQuestion({
        question: 'Việt Nam gia nhập WTO năm nào?',
        top_k: 5,
        search_mode: 'hybrid',
      });

      expect(fetchSpy).toHaveBeenCalledTimes(1);
      expect(String(fetchSpy.mock.calls[0][0])).toContain('/questions/ask');
      expect(result.status).toBe('SUPPORTED');
      expect(result.citations[0].footnote_index).toBe(1);
      expect(result.citations[0].stance).toBe('SUPPORTS');
      expect(result.evidence[0].evidence_id).toBe('E1');
    });

    it('verificationService.verifyText calls /verify and unwraps VerificationResultResponse with evidence stance', async () => {
      const mockResult = {
        request_id: 'req-999',
        status: 'COMPLETED',
        overall_verdict: 'TRUE',
        summary: 'Tất cả các khẳng định đều đúng.',
        claims_count: 1,
        claims: [
          {
            claim_id: 'cl-1',
            claim_text: 'Thủ đô của Việt Nam là Hà Nội.',
            verdict: 'SUPPORTED',
            confidence_score: 0.99,
            explanation: 'Khẳng định chính xác theo địa lý.',
            evidences: [
              {
                source_title: 'Cổng thông tin Chính phủ',
                snippet: 'Hà Nội là thủ đô của nước CHXHCN Việt Nam.',
                stance: 'SUPPORTS',
                relevance_score: 0.98,
              },
            ],
          },
        ],
        created_at: '2026-09-14T00:00:00Z',
      };

      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: mockResult }),
      } as Response);

      const result = await verificationService.verifyText({
        text: 'Thủ đô của Việt Nam là Hà Nội.',
        enable_contradiction_check: true,
      });

      expect(fetchSpy).toHaveBeenCalledTimes(1);
      expect(String(fetchSpy.mock.calls[0][0])).toContain('/verify');
      expect(result.overall_verdict).toBe('TRUE');
      expect(result.claims[0].evidences[0].stance).toBe('SUPPORTS');
    });

    it('documentService handles upload returning document_id and ingest returning id', async () => {
      // 1. Upload mock
      vi.spyOn(globalThis, 'fetch')
        .mockResolvedValueOnce({
          ok: true,
          status: 201,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            data: {
              document_id: 'doc-uuid-upload-1',
              title: 'report.pdf',
              doc_type: 'pdf',
              page_count: 3,
              total_chunks: 5,
              metadata: {},
              chunks: [],
            },
          }),
        } as Response)
        // 2. Ingest mock
        .mockResolvedValueOnce({
          ok: true,
          status: 201,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            data: {
              id: 'doc-uuid-ingest-2',
              title: 'raw_article.txt',
              source_url: 'https://example.com',
              doc_type: 'text',
              created_at: '2026-09-14T00:00:00Z',
              chunk_count: 2,
            },
          }),
        } as Response);

      const uploadResult = await documentService.uploadDocument({
        file: new File(['dummy'], 'report.pdf', { type: 'application/pdf' }),
        chunk_strategy: 'fixed',
      });
      expect(uploadResult.document_id).toBe('doc-uuid-upload-1');

      const ingestResult = await documentService.ingestDocument({
        title: 'raw_article.txt',
        raw_content: 'sample text',
      });
      expect(ingestResult.id).toBe('doc-uuid-ingest-2');
    });

    it('searchService.search passes mode parameter correctly', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          success: true,
          data: {
            query: 'kinh tế',
            search_type: 'hybrid',
            total_hits: 1,
            hits: [
              {
                chunk_id: 'ch-1',
                content: 'Tăng trưởng kinh tế...',
                score: 0.88,
              },
            ],
          },
        }),
      } as Response);

      const result = await searchService.search({ query: 'kinh tế', top_k: 5 }, 'hybrid');

      expect(String(fetchSpy.mock.calls[0][0])).toContain('/search?mode=hybrid');
      expect(result.hits[0].chunk_id).toBe('ch-1');
    });

    it('systemService calls root health and ready endpoints with rawPath', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch')
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ status: 'healthy', service: 'SourceCheck AI', environment: 'dev' }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ status: 'ready', database: 'connected', redis: 'connected', vector_db: 'connected' }),
        } as Response);

      const health = await systemService.getHealth();
      expect(health.status).toBe('healthy');
      expect(String(fetchSpy.mock.calls[0][0])).toBe('/health');

      const readiness = await systemService.getReadiness();
      expect(readiness.status).toBe('ready');
      expect(String(fetchSpy.mock.calls[1][0])).toBe('/ready');
    });
  });
});
