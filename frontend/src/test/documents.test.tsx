/**
 * Test Suite for Document Management & Knowledge Base (FE-04.5A).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DocumentsPage } from '../pages/DocumentsPage';
import { documentService } from '../services/documents';
import { ApiClientError } from '../services/apiClient';
import {
  DocumentResponse,
  DocumentDetailResponse,
  DocumentUploadResponse,
} from '../types/document';
import { PaginatedResponse } from '../types/common';

const mockDoc1: DocumentResponse = {
  id: 'doc-uuid-001',
  title: 'Nghị định số 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân',
  source_url: 'https://chinhphu.vn/nghi-dinh-13',
  publisher: 'Chính phủ',
  doc_type: 'pdf',
  created_at: '2026-09-15T08:30:00Z',
  updated_at: '2026-09-15T08:30:00Z',
  chunk_count: 12,
  doc_metadata: { author: 'Ban soạn thảo', year: 2023 },
};

const mockDoc2: DocumentResponse = {
  id: 'doc-uuid-002',
  title: 'Báo cáo Tổng kết Kinh tế - Xã hội năm 2024',
  source_url: 'https://gso.gov.vn/bao-cao-2024',
  publisher: 'Tổng cục Thống kê',
  doc_type: 'docx',
  created_at: '2026-09-15T09:15:00Z',
  updated_at: '2026-09-15T09:15:00Z',
  chunk_count: 25,
  doc_metadata: { department: 'GSO' },
};

const mockPaginatedDocs: PaginatedResponse<DocumentResponse> = {
  items: [mockDoc1, mockDoc2],
  total: 2,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockDocDetail: DocumentDetailResponse = {
  ...mockDoc1,
  raw_content: 'Đây là toàn bộ nội dung văn bản Nghị định số 13/2023/NĐ-CP được lưu trong cơ sở tri thức.',
  chunks: [
    {
      id: 'chunk-001',
      chunk_index: 0,
      content: 'Chương I: Những quy định chung. Điều 1: Phạm vi điều chỉnh và đối tượng áp dụng.',
      chunk_metadata: { page_number: 1, section: 'Chương I' },
    },
    {
      id: 'chunk-002',
      chunk_index: 1,
      content: 'Điều 2: Giải thích từ ngữ. Dữ liệu cá nhân là thông tin dưới dạng ký hiệu, chữ viết, chữ số, hình ảnh...',
      chunk_metadata: { page_number: 2, section: 'Chương I' },
    },
  ],
};

const mockUploadSuccess: DocumentUploadResponse = {
  document_id: 'doc-uuid-new',
  title: 'Luat_Giao_Dich_Dien_Tu_2023.pdf',
  doc_type: 'pdf',
  page_count: 45,
  total_chunks: 18,
  metadata: { filename: 'Luat_Giao_Dich_Dien_Tu_2023.pdf' },
  chunks: [],
};

describe('Documents & Knowledge Base Feature (FE-04.5A)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('1. Initial Load & Document List', () => {
    it('renders loading state initially while fetching documents', async () => {
      let resolveList: (data: any) => void;
      const listPromise = new Promise((resolve) => {
        resolveList = resolve;
      });
      vi.spyOn(documentService, 'listDocuments').mockImplementationOnce(() => listPromise as any);

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      // Verify Loading indicator
      expect(screen.getByTestId('documents-loading-state')).toBeInTheDocument();
      expect(screen.getByText(/đang tải danh sách tài liệu/i)).toBeInTheDocument();

      // Resolve API
      resolveList!(mockPaginatedDocs);

      await waitFor(() => {
        expect(screen.queryByTestId('documents-loading-state')).not.toBeInTheDocument();
        expect(screen.getByTestId('documents-list-section')).toBeInTheDocument();
      });
    });

    it('renders document table with correct columns, titles, doc types, chunk counts, and publishers', async () => {
      vi.spyOn(documentService, 'listDocuments').mockResolvedValueOnce(mockPaginatedDocs);

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('documents-table')).toBeInTheDocument();
      });

      // Check Doc 1
      const docRow1 = screen.getByTestId('doc-row-doc-uuid-001');
      expect(within(docRow1).getByTestId('doc-title-link-doc-uuid-001')).toHaveTextContent(
        'Nghị định số 13/2023/NĐ-CP'
      );
      expect(within(docRow1).getByTestId('doc-publisher-doc-uuid-001')).toHaveTextContent('Chính phủ');
      expect(within(docRow1).getByTestId('doc-type-badge-doc-uuid-001')).toHaveTextContent('PDF');
      expect(within(docRow1).getByTestId('doc-chunk-count-doc-uuid-001')).toHaveTextContent('12');

      // Check Doc 2
      const docRow2 = screen.getByTestId('doc-row-doc-uuid-002');
      expect(within(docRow2).getByTestId('doc-title-link-doc-uuid-002')).toHaveTextContent(
        'Báo cáo Tổng kết Kinh tế - Xã hội'
      );
      expect(within(docRow2).getByTestId('doc-publisher-doc-uuid-002')).toHaveTextContent('Tổng cục Thống kê');
      expect(within(docRow2).getByTestId('doc-type-badge-doc-uuid-002')).toHaveTextContent('DOCX');
      expect(within(docRow2).getByTestId('doc-chunk-count-doc-uuid-002')).toHaveTextContent('25');
    });

    it('renders empty state when knowledge base has zero documents', async () => {
      vi.spyOn(documentService, 'listDocuments').mockResolvedValueOnce({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('documents-empty-state')).toBeInTheDocument();
      });

      expect(screen.getByText('Chưa có tài liệu nào trong Cơ sở tri thức')).toBeInTheDocument();
      expect(screen.getByTestId('btn-empty-upload')).toBeInTheDocument();
    });

    it('renders error alert when API fetch fails', async () => {
      vi.spyOn(documentService, 'listDocuments').mockRejectedValueOnce(
        new ApiClientError('Không thể nạp dữ liệu từ máy chủ.', 500)
      );

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('documents-error-alert')).toBeInTheDocument();
      });
      expect(screen.getByText(/không thể tải danh sách tài liệu do lỗi máy chủ/i)).toBeInTheDocument();
    });

    it('refreshes document list when clicking refresh button', async () => {
      const listSpy = vi.spyOn(documentService, 'listDocuments').mockResolvedValue(mockPaginatedDocs);

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('documents-table')).toBeInTheDocument();
      });

      expect(listSpy).toHaveBeenCalledTimes(1);

      const refreshBtn = screen.getByTestId('btn-refresh-documents');
      fireEvent.click(refreshBtn);

      expect(listSpy).toHaveBeenCalledTimes(2);
    });

    it('filters documents locally when searching in the table search input', async () => {
      vi.spyOn(documentService, 'listDocuments').mockResolvedValueOnce(mockPaginatedDocs);

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('documents-table')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('document-search-input');
      fireEvent.change(searchInput, { target: { value: 'Nghị định' } });

      // Doc 1 visible, Doc 2 hidden
      expect(screen.getByTestId('doc-row-doc-uuid-001')).toBeInTheDocument();
      expect(screen.queryByTestId('doc-row-doc-uuid-002')).not.toBeInTheDocument();

      // Clear search
      fireEvent.change(searchInput, { target: { value: '' } });
      expect(screen.getByTestId('doc-row-doc-uuid-001')).toBeInTheDocument();
      expect(screen.getByTestId('doc-row-doc-uuid-002')).toBeInTheDocument();
    });
  });

  describe('2. Document Upload Modal & Validation', () => {
    it('opens and closes DocumentUploadModal properly', async () => {
      vi.spyOn(documentService, 'listDocuments').mockResolvedValueOnce(mockPaginatedDocs);

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('btn-open-upload-modal')).toBeInTheDocument();
      });

      // Open Modal
      fireEvent.click(screen.getByTestId('btn-open-upload-modal'));
      expect(screen.getByTestId('upload-modal-card')).toBeInTheDocument();
      expect(screen.getByText('Nạp tài liệu vào Cơ sở tri thức')).toBeInTheDocument();

      // Close Modal via close button
      fireEvent.click(screen.getByTestId('btn-close-upload-modal'));
      expect(screen.queryByTestId('upload-modal-card')).not.toBeInTheDocument();
    });

    it('rejects unsupported file formats with user-friendly error message', async () => {
      vi.spyOn(documentService, 'listDocuments').mockResolvedValueOnce(mockPaginatedDocs);

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('btn-open-upload-modal'));

      const fileInput = screen.getByTestId('file-input');
      const invalidFile = new File(['dummy content'], 'image.png', { type: 'image/png' });

      fireEvent.change(fileInput, { target: { files: [invalidFile] } });

      await waitFor(() => {
        expect(screen.getByTestId('upload-error-alert')).toBeInTheDocument();
      });
      expect(screen.getByText(/định dạng tệp không được hỗ trợ/i)).toBeInTheDocument();
      expect(screen.getByTestId('btn-submit-upload')).toBeDisabled();
    });

    it('accepts valid PDF file and submits upload to documentService', async () => {
      vi.spyOn(documentService, 'listDocuments').mockResolvedValue(mockPaginatedDocs);
      const uploadSpy = vi.spyOn(documentService, 'uploadDocument').mockResolvedValueOnce(mockUploadSuccess);

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('btn-open-upload-modal'));

      const fileInput = screen.getByTestId('file-input');
      const validFile = new File(['valid pdf content'], 'Luat_Giao_Dich_Dien_Tu_2023.pdf', {
        type: 'application/pdf',
      });

      fireEvent.change(fileInput, { target: { files: [validFile] } });

      // Selected file preview visible
      expect(screen.getByTestId('selected-file-name')).toHaveTextContent('Luat_Giao_Dich_Dien_Tu_2023.pdf');
      const submitBtn = screen.getByTestId('btn-submit-upload');
      expect(submitBtn).not.toBeDisabled();

      // Submit
      fireEvent.click(submitBtn);

      expect(uploadSpy).toHaveBeenCalledTimes(1);
      expect(uploadSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          file: validFile,
          chunk_strategy: 'fixed',
        })
      );

      await waitFor(() => {
        expect(screen.getByTestId('upload-success-alert')).toBeInTheDocument();
      });
    });

    it('handles upload failure gracefully displaying error alert', async () => {
      vi.spyOn(documentService, 'listDocuments').mockResolvedValue(mockPaginatedDocs);
      vi.spyOn(documentService, 'uploadDocument').mockRejectedValueOnce(
        new ApiClientError('Tệp PDF bị lỗi cấu trúc hoặc có mật khẩu bảo vệ.', 400)
      );

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('btn-open-upload-modal'));

      const fileInput = screen.getByTestId('file-input');
      const file = new File(['corrupted'], 'corrupted.pdf', { type: 'application/pdf' });
      fireEvent.change(fileInput, { target: { files: [file] } });

      fireEvent.click(screen.getByTestId('btn-submit-upload'));

      await waitFor(() => {
        expect(screen.getByTestId('upload-error-alert')).toBeInTheDocument();
        expect(screen.getByText('Tệp PDF bị lỗi cấu trúc hoặc có mật khẩu bảo vệ.')).toBeInTheDocument();
      });
    });
  });

  describe('3. Document Detail & Chunk Viewer', () => {
    it('opens DocumentChunkViewer and displays chunk list with index, content, and metadata', async () => {
      vi.spyOn(documentService, 'listDocuments').mockResolvedValueOnce(mockPaginatedDocs);
      const getDocSpy = vi.spyOn(documentService, 'getDocument').mockResolvedValueOnce(mockDocDetail);

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('btn-view-doc-doc-uuid-001')).toBeInTheDocument();
      });

      // Click view on Doc 1
      fireEvent.click(screen.getByTestId('btn-view-doc-doc-uuid-001'));

      expect(getDocSpy).toHaveBeenCalledWith('doc-uuid-001');

      await waitFor(() => {
        expect(screen.getByTestId('chunk-viewer-modal')).toBeInTheDocument();
      });

      // Verify Header & Stats Strip
      expect(screen.getByTestId('viewer-doc-title')).toHaveTextContent('Nghị định số 13/2023/NĐ-CP');
      expect(screen.getByTestId('viewer-chunks-count')).toHaveTextContent('2 chunks');
      expect(screen.getByTestId('viewer-ingestion-status')).toHaveTextContent('Đã lập chỉ mục');

      // Verify Chunks Accordion List
      expect(screen.getByTestId('chunk-card-0')).toBeInTheDocument();
      expect(screen.getByTestId('chunk-card-1')).toBeInTheDocument();
      expect(screen.getByTestId('chunk-index-0')).toHaveTextContent('Chunk #0');
      expect(screen.getByTestId('chunk-content-0')).toHaveTextContent('Chương I: Những quy định chung');

      // Toggle Raw Content tab
      fireEvent.click(screen.getByTestId('tab-view-raw'));
      expect(screen.getByTestId('raw-content-text')).toHaveTextContent('Đây là toàn bộ nội dung văn bản');

      // Toggle Metadata tab
      fireEvent.click(screen.getByTestId('tab-view-metadata'));
      expect(screen.getByTestId('meta-val-id')).toHaveTextContent('doc-uuid-001');
      expect(screen.getByTestId('doc-custom-metadata-pre')).toHaveTextContent('"author": "Ban soạn thảo"');

      // Close modal
      fireEvent.click(screen.getByTestId('btn-close-chunk-viewer'));
      expect(screen.queryByTestId('chunk-viewer-modal')).not.toBeInTheDocument();
    });

    it('handles 404 error when opening non-existent document detail', async () => {
      vi.spyOn(documentService, 'listDocuments').mockResolvedValueOnce(mockPaginatedDocs);
      vi.spyOn(documentService, 'getDocument').mockRejectedValueOnce(
        new ApiClientError('Document not found', 404)
      );

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('btn-view-doc-doc-uuid-001')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-view-doc-doc-uuid-001'));

      await waitFor(() => {
        expect(screen.getByTestId('documents-error-alert')).toBeInTheDocument();
        expect(screen.getByText(/không tồn tại hoặc đã bị xóa/i)).toBeInTheDocument();
      });
    });
  });

  describe('4. Delete Document & Cascade Safety', () => {
    it('prompts delete confirmation modal before deleting', async () => {
      vi.spyOn(documentService, 'listDocuments').mockResolvedValueOnce(mockPaginatedDocs);

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('btn-delete-doc-doc-uuid-001')).toBeInTheDocument();
      });

      // Click delete button
      fireEvent.click(screen.getByTestId('btn-delete-doc-doc-uuid-001'));

      // Modal appears
      expect(screen.getByTestId('delete-doc-modal-card')).toBeInTheDocument();
      expect(screen.getByText('Xác nhận xóa tài liệu')).toBeInTheDocument();
      expect(screen.getByTestId('btn-confirm-delete')).toBeInTheDocument();

      // Cancel button dismisses modal
      fireEvent.click(screen.getByTestId('btn-cancel-delete'));
      expect(screen.queryByTestId('delete-doc-modal-card')).not.toBeInTheDocument();
    });

    it('calls documentService.deleteDocument on confirmation and refreshes list', async () => {
      const listSpy = vi.spyOn(documentService, 'listDocuments')
        .mockResolvedValueOnce(mockPaginatedDocs)
        .mockResolvedValueOnce({
          items: [mockDoc2],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        });

      const deleteSpy = vi.spyOn(documentService, 'deleteDocument').mockResolvedValueOnce({
        document_id: 'doc-uuid-001',
        title: 'Nghị định số 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân',
      });

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('btn-delete-doc-doc-uuid-001')).toBeInTheDocument();
      });

      // Click delete and confirm
      fireEvent.click(screen.getByTestId('btn-delete-doc-doc-uuid-001'));
      fireEvent.click(screen.getByTestId('btn-confirm-delete'));

      expect(deleteSpy).toHaveBeenCalledWith('doc-uuid-001');

      await waitFor(() => {
        expect(screen.getByTestId('action-success-alert')).toBeInTheDocument();
      });
      expect(screen.getByText(/đã xóa thành công tài liệu/i)).toBeInTheDocument();
      expect(listSpy).toHaveBeenCalledTimes(2);
    });

    it('displays error alert if delete API fails', async () => {
      vi.spyOn(documentService, 'listDocuments').mockResolvedValueOnce(mockPaginatedDocs);
      vi.spyOn(documentService, 'deleteDocument').mockRejectedValueOnce(
        new ApiClientError('Không có quyền xóa tài liệu này.', 403)
      );

      render(
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('btn-delete-doc-doc-uuid-001')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-delete-doc-doc-uuid-001'));
      fireEvent.click(screen.getByTestId('btn-confirm-delete'));

      await waitFor(() => {
        expect(screen.getByTestId('documents-error-alert')).toBeInTheDocument();
        expect(screen.getByText('Không có quyền xóa tài liệu này.')).toBeInTheDocument();
      });
    });
  });
});
