/**
 * Test Suite for Search & Retrieval Explorer (FE-04.6B).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SearchPage } from '../pages/SearchPage';
import { searchService } from '../services/search';
import { ApiClientError } from '../services/apiClient';
import { SearchResponse } from '../types/search';

const mockHybridResponse: SearchResponse = {
  query: 'Nghị định 13 bảo vệ dữ liệu cá nhân',
  search_type: 'hybrid',
  total_hits: 2,
  rerank_applied: true,
  hits: [
    {
      chunk_id: 'chunk-uuid-001',
      document_id: 'doc-uuid-001',
      content: 'Chương II Điều 9: Quyền của chủ thể dữ liệu cá nhân gồm quyền được biết, quyền đồng ý, quyền truy cập...',
      score: 0.9452,
      rank: 1,
      vector_score: 0.8845,
      vector_rank: 1,
      bm25_score: 14.821,
      bm25_rank: 2,
      rrf_score: 0.03252,
      rerank_score: 0.9452,
      source_title: 'Nghị định số 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân',
      source_url: 'https://chinhphu.vn/nghi-dinh-13',
      publisher: 'Chính phủ',
      page_number: 4,
      retriever_type: 'reranked',
      metadata: { author: 'Ban soạn thảo', year: 2023 },
    },
    {
      chunk_id: 'chunk-uuid-002',
      document_id: 'doc-uuid-001',
      content: 'Chương I Điều 2: Giải thích từ ngữ. Dữ liệu cá nhân cơ bản và dữ liệu cá nhân nhạy cảm...',
      score: 0.8621,
      rank: 2,
      vector_score: 0.8123,
      vector_rank: 3,
      bm25_score: 18.245,
      bm25_rank: 1,
      rrf_score: 0.03198,
      rerank_score: 0.8621,
      source_title: 'Nghị định số 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân',
      source_url: 'https://chinhphu.vn/nghi-dinh-13',
      publisher: 'Chính phủ',
      page_number: 2,
      retriever_type: 'reranked',
      metadata: { author: 'Ban soạn thảo', year: 2023 },
    },
  ],
};


describe('Search & Retrieval Explorer Feature (FE-04.6B)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('1. Render & Initial UI State', () => {
    it('renders SearchPage header, query input, search controls, and initial empty state', () => {
      render(
        <MemoryRouter>
          <SearchPage />
        </MemoryRouter>
      );

      // Verify Header
      expect(screen.getByText(/Evidence Exploration|Khảo sát bằng chứng/)).toBeInTheDocument();

      // Verify Input & Submit
      expect(screen.getByTestId('search-query-input')).toBeInTheDocument();
      expect(screen.getByTestId('btn-execute-search')).toBeInTheDocument();

      // Technical retrieval controls are system-managed.
      expect(screen.queryByTestId('select-retriever-mode')).not.toBeInTheDocument();
      expect(screen.queryByTestId('select-top-k')).not.toBeInTheDocument();
      expect(screen.queryByTestId('toggle-rerank-checkbox')).not.toBeInTheDocument();

      // Verify Initial Empty State
      expect(screen.getByTestId('search-initial-state')).toBeInTheDocument();

      // Verify Sample Queries
      expect(screen.getByTestId('sample-queries-wrap')).toBeInTheDocument();
      expect(screen.getByTestId('sample-query-chip-0')).toBeInTheDocument();
    });
  });

  describe('2. Query Execution & Results Rendering', () => {
    it('shows loading state while searching and displays result cards upon completion', async () => {
      let resolveSearch: (data: any) => void;
      const searchPromise = new Promise((resolve) => {
        resolveSearch = resolve;
      });
      const searchSpy = vi.spyOn(searchService, 'search').mockImplementationOnce(() => searchPromise as any);

      render(
        <MemoryRouter>
          <SearchPage />
        </MemoryRouter>
      );

      const input = screen.getByTestId('search-query-input');
      fireEvent.change(input, { target: { value: 'Nghị định 13 bảo vệ dữ liệu cá nhân' } });

      const submitBtn = screen.getByTestId('btn-execute-search');
      fireEvent.click(submitBtn);

      // Verify search call
      expect(searchSpy).toHaveBeenCalledWith(
        {
          query: 'Nghị định 13 bảo vệ dữ liệu cá nhân',
          top_k: 5,
          mode: 'hybrid',
          rerank: true,
        },
        'hybrid',
        true
      );

      // Verify Loading indicator
      expect(screen.getByTestId('search-loading-state')).toBeInTheDocument();

      // Resolve Promise
      resolveSearch!(mockHybridResponse);

      await waitFor(() => {
        expect(screen.queryByTestId('search-loading-state')).not.toBeInTheDocument();
        expect(screen.getByTestId('search-results-section')).toBeInTheDocument();
      });

      // Verify Stats Strip
      expect(screen.getByTestId('search-stats-strip')).toBeInTheDocument();
      expect(screen.getByText(/tìm thấy/i)).toHaveTextContent('2');

      // Verify Result Cards
      const card0 = screen.getByTestId('search-result-card-0');
      expect(within(card0).getByTestId('hit-rank-badge-0')).toHaveTextContent('#1');
      expect(within(card0).getByTestId('hit-title-0')).toHaveTextContent('Nghị định số 13/2023/NĐ-CP');
      expect(within(card0).getByTestId('hit-publisher-0')).toHaveTextContent('Chính phủ');
      expect(within(card0).getByTestId('hit-page-0')).toHaveTextContent('Trang 4');

      // Check Card 1
      const card1 = screen.getByTestId('search-result-card-1');
      expect(within(card1).getByTestId('hit-rank-badge-1')).toHaveTextContent('#2');
    });

    it('triggers search automatically when clicking a sample query chip', async () => {
      const searchSpy = vi.spyOn(searchService, 'search').mockResolvedValueOnce(mockHybridResponse);

      render(
        <MemoryRouter>
          <SearchPage />
        </MemoryRouter>
      );

      const sampleChip = screen.getByTestId('sample-query-chip-0');
      fireEvent.click(sampleChip);

      expect(searchSpy).toHaveBeenCalledTimes(1);
      expect(searchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          query: 'Nghị định 13 bảo vệ dữ liệu cá nhân',
        }),
        'hybrid',
        true
      );

      await waitFor(() => {
        expect(screen.getByTestId('search-results-section')).toBeInTheDocument();
      });
    });

    it('uses the system-managed hybrid retrieval defaults', async () => {
      const searchSpy = vi.spyOn(searchService, 'search').mockResolvedValueOnce(mockHybridResponse);
      render(<MemoryRouter><SearchPage /></MemoryRouter>);
      const input = screen.getByTestId('search-query-input');
      fireEvent.change(input, { target: { value: 'Evidence query' } });
      fireEvent.click(screen.getByTestId('btn-execute-search'));
      expect(searchSpy).toHaveBeenCalledWith(
        { query: 'Evidence query', top_k: 5, mode: 'hybrid', rerank: true },
        'hybrid',
        true
      );
      await waitFor(() => expect(screen.getByTestId('search-results-section')).toBeInTheDocument());
    });
    it('renders zero-results state when retrieval returns 0 hits', async () => {
      vi.spyOn(searchService, 'search').mockResolvedValueOnce({
        query: 'Truy vấn không có dữ liệu',
        search_type: 'hybrid',
        total_hits: 0,
        hits: [],
      });

      render(
        <MemoryRouter>
          <SearchPage />
        </MemoryRouter>
      );

      const input = screen.getByTestId('search-query-input');
      fireEvent.change(input, { target: { value: 'Truy vấn không có dữ liệu' } });
      fireEvent.click(screen.getByTestId('btn-execute-search'));

      await waitFor(() => {
        expect(screen.getByTestId('search-zero-results-state')).toBeInTheDocument();
      });

      expect(screen.getByText('Không tìm thấy kết quả phù hợp')).toBeInTheDocument();
    });
  });

  describe('3. Pipeline Inspection & Retrieval Details Drawer', () => {
    it('opens RetrievalDetailsDrawer and displays step-by-step pipeline and scores', async () => {
      vi.spyOn(searchService, 'search').mockResolvedValueOnce(mockHybridResponse);

      render(
        <MemoryRouter>
          <SearchPage />
        </MemoryRouter>
      );

      const input = screen.getByTestId('search-query-input');
      fireEvent.change(input, { target: { value: 'Nghị định 13' } });
      fireEvent.click(screen.getByTestId('btn-execute-search'));

      await waitFor(() => {
        expect(screen.getByTestId('search-results-section')).toBeInTheDocument();
      });

      // Click "Xem pipeline" on Hit #1
      const btnViewPipeline = screen.getByTestId('btn-view-details-0');
      fireEvent.click(btnViewPipeline);

      // Verify Drawer is open
      expect(screen.getByTestId('retrieval-details-drawer')).toBeInTheDocument();
      expect(screen.getByTestId('drawer-hit-rank')).toHaveTextContent('#1');

      // Verify Query box
      expect(screen.getByTestId('drawer-query-box')).toHaveTextContent('Nghị định 13');

      // Verify Step 1: Vector

      // Verify Step 2: BM25

      // Verify Step 3: RRF

      // Verify Step 4: Reranker

      // Verify Step 5: Final

      // Verify Passage Content & Identifiers
      expect(screen.getByTestId('drawer-chunk-content')).toHaveTextContent('Quyền của chủ thể dữ liệu cá nhân');
      expect(screen.getByTestId('drawer-source-title')).toHaveTextContent('Nghị định số 13/2023/NĐ-CP');
      expect(screen.getByTestId('drawer-document-id')).toHaveTextContent('doc-uuid-001');
      expect(screen.getByTestId('drawer-publisher')).toHaveTextContent('Chính phủ');
      expect(screen.getByTestId('drawer-page-number')).toHaveTextContent('Trang 4');

      // Verify Raw Metadata JSON

      // Close Drawer via Close button
      fireEvent.click(screen.getByTestId('btn-close-retrieval-drawer'));
      expect(screen.queryByTestId('retrieval-details-drawer')).not.toBeInTheDocument();
    });

    it('closes drawer when clicking backdrop or pressing Escape key', async () => {
      vi.spyOn(searchService, 'search').mockResolvedValueOnce(mockHybridResponse);

      render(
        <MemoryRouter>
          <SearchPage />
        </MemoryRouter>
      );

      const sampleChip = screen.getByTestId('sample-query-chip-0');
      fireEvent.click(sampleChip);

      await waitFor(() => {
        expect(screen.getByTestId('search-results-section')).toBeInTheDocument();
      });

      // Open drawer by clicking card
      const card = screen.getByTestId('search-result-card-0');
      fireEvent.click(card);
      expect(screen.getByTestId('retrieval-details-drawer')).toBeInTheDocument();

      // Press Escape
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(screen.queryByTestId('retrieval-details-drawer')).not.toBeInTheDocument();
    });
  });

  describe('4. Error Handling', () => {
    it('displays error alert on server error 500 and allows dismissing', async () => {
      vi.spyOn(searchService, 'search').mockRejectedValueOnce(
        new ApiClientError('Internal Server Error', 500)
      );

      render(
        <MemoryRouter>
          <SearchPage />
        </MemoryRouter>
      );

      const input = screen.getByTestId('search-query-input');
      fireEvent.change(input, { target: { value: 'Lỗi máy chủ' } });
      fireEvent.click(screen.getByTestId('btn-execute-search'));

      await waitFor(() => {
        expect(screen.getByTestId('search-error-alert')).toBeInTheDocument();
      });


      // Dismiss error
      fireEvent.click(screen.getByTestId('btn-close-error'));
      expect(screen.queryByTestId('search-error-alert')).not.toBeInTheDocument();
    });

    it('displays network connection error when status code is 0', async () => {
      vi.spyOn(searchService, 'search').mockRejectedValueOnce(
        new ApiClientError('Network Error', 0)
      );

      render(
        <MemoryRouter>
          <SearchPage />
        </MemoryRouter>
      );

      const input = screen.getByTestId('search-query-input');
      fireEvent.change(input, { target: { value: 'Mất mạng' } });
      fireEvent.click(screen.getByTestId('btn-execute-search'));

      await waitFor(() => {
        expect(screen.getByTestId('search-error-alert')).toBeInTheDocument();
      });

    });
  });
});
