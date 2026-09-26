import React, { useState, useEffect, useCallback } from 'react';
import { documentService } from '../services/documents';
import { DocumentResponse, DocumentDetailResponse } from '../types/document';
import { useAIPreferences } from '../hooks/useAIPreferences';
import { ApiClientError } from '../services/apiClient';
import { DocumentTable } from '../components/documents/DocumentTable';
import { DocumentUploadModal } from '../components/documents/DocumentUploadModal';
import { DocumentChunkViewer } from '../components/documents/DocumentChunkViewer';
import '../styles/documents.css';

export const DocumentsPage: React.FC = () => {
  const { t } = useAIPreferences();
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Pagination state
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [total, setTotal] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);

  // Modals & Viewers state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [selectedDocumentDetail, setSelectedDocumentDetail] = useState<DocumentDetailResponse | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [documentToDelete, setDocumentToDelete] = useState<DocumentResponse | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const fetchDocuments = useCallback(async (targetPage = page, targetPageSize = pageSize) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await documentService.listDocuments({
        page: targetPage,
        page_size: targetPageSize,
      });

      setDocuments(response.items || []);
      setTotal(response.total || 0);
      setPage(response.page || 1);
      setPageSize(response.page_size || 20);
      setTotalPages(response.total_pages || 1);
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        if (err.statusCode === 401) {
          setError('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.');
        } else if (err.statusCode >= 500) {
          setError('Không thể tải danh sách tài liệu do lỗi máy chủ (500).');
        } else if (err.statusCode === 0) {
          setError('Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại kết nối mạng.');
        } else {
          setError(err.message || 'Lỗi khi tải danh sách tài liệu.');
        }
      } else {
        setError(err?.message || 'Đã xảy ra lỗi không xác định.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    fetchDocuments(1, pageSize);
  }, []);

  const handleRefresh = () => {
    fetchDocuments(page, pageSize);
  };

  const handleViewDocument = async (docId: string) => {
    setIsLoadingDetail(true);
    setError(null);
    try {
      const detail = await documentService.getDocument(docId);
      setSelectedDocumentDetail(detail);
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        if (err.statusCode === 404) {
          setError(`Tài liệu với ID '${docId}' không tồn tại hoặc đã bị xóa.`);
        } else {
          setError(err.message || 'Không thể lấy thông tin chi tiết tài liệu.');
        }
      } else {
        setError(err?.message || 'Lỗi khi xem chi tiết tài liệu.');
      }
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!documentToDelete || isDeleting) return;

    setIsDeleting(true);
    setError(null);
    const targetDoc = documentToDelete;

    try {
      await documentService.deleteDocument(targetDoc.id);

      setActionSuccess(`Đã xóa thành công tài liệu "${targetDoc.title}".`);
      setTimeout(() => setActionSuccess(null), 4000);

      // Close modal & viewers
      setDocumentToDelete(null);
      if (selectedDocumentDetail?.id === targetDoc.id) {
        setSelectedDocumentDetail(null);
      }

      // Re-fetch documents
      await fetchDocuments(page, pageSize);
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        setError(err.message || 'Không thể xóa tài liệu. Vui lòng thử lại.');
      } else {
        setError(err?.message || 'Lỗi không xác định khi xóa tài liệu.');
      }
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="documents-container" data-testid="documents-page">
      {/* Page Header */}
      <div className="documents-header">
        <div className="header-info">
          <h1>{t('documents.title')}</h1>
          <p>{t('documents.description')}</p>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="btn-refresh"
            onClick={handleRefresh}
            disabled={isLoading}
            title="Tải lại danh sách"
            data-testid="btn-refresh-documents"
          >
            <svg
              className={isLoading ? 'spinning' : ''}
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            <span>Làm mới</span>
          </button>

          <button
            type="button"
            className="btn-upload-primary"
            onClick={() => setIsUploadModalOpen(true)}
            data-testid="btn-open-upload-modal"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>Nạp tài liệu mới</span>
          </button>
        </div>
      </div>

      {/* Action Success Alert */}
      {actionSuccess && (
        <div className="doc-alert success" role="status" data-testid="action-success-alert">
          <span>✓ {actionSuccess}</span>
          <button type="button" onClick={() => setActionSuccess(null)} className="alert-close-btn">✕</button>
        </div>
      )}

      {/* Global Error Alert */}
      {error && (
        <div className="doc-alert danger" role="alert" data-testid="documents-error-alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} className="alert-close-btn">✕</button>
        </div>
      )}

      {/* Loading Detail Spinner Indicator */}
      {isLoadingDetail && (
        <div className="detail-loading-indicator" data-testid="detail-loading-indicator">
          <div className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px' }} />
          <span>Đang tải thông tin chi tiết...</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="documents-loading-state" data-testid="documents-loading-state">
          <div className="spinner" style={{ width: '36px', height: '36px', borderWidth: '3px' }} />
          <p>{t('documents.loading')}</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && documents.length === 0 && (
        <div className="documents-empty-state" data-testid="documents-empty-state">
          <div className="empty-icon-wrap">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="12" y1="18" x2="12" y2="12" />
              <line x1="9" y1="15" x2="15" y2="15" />
            </svg>
          </div>
          <h3>Chưa có tài liệu nào trong Cơ sở tri thức</h3>
          <p>
            Tải lên PDF, DOCX hoặc TXT để bắt đầu xây dựng bộ nguồn tham khảo,
            phục vụ việc hỏi đáp và kiểm chứng thông tin.
          </p>
          <button
            type="button"
            className="btn-upload-primary"
            onClick={() => setIsUploadModalOpen(true)}
            data-testid="btn-empty-upload"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>Tải lên tài liệu đầu tiên</span>
          </button>
        </div>
      )}

      {/* Documents List & Table */}
      {!isLoading && documents.length > 0 && (
        <div className="documents-content-section" data-testid="documents-list-section">
          <DocumentTable
            documents={documents}
            onViewDocument={handleViewDocument}
            onDeleteDocument={(doc) => setDocumentToDelete(doc)}
          />

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="documents-pagination-bar" data-testid="documents-pagination">
              <div className="pagination-info">
                Trang <strong>{page}</strong> / {totalPages} (Tổng {total} tài liệu)
              </div>
              <div className="pagination-buttons">
                <button
                  type="button"
                  className="btn-page"
                  disabled={page <= 1 || isLoading}
                  onClick={() => {
                    const newPage = page - 1;
                    setPage(newPage);
                    fetchDocuments(newPage, pageSize);
                  }}
                  data-testid="btn-prev-page"
                >
                  ← Trước
                </button>
                <button
                  type="button"
                  className="btn-page"
                  disabled={page >= totalPages || isLoading}
                  onClick={() => {
                    const newPage = page + 1;
                    setPage(newPage);
                    fetchDocuments(newPage, pageSize);
                  }}
                  data-testid="btn-next-page"
                >
                  Sau →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={() => {
          fetchDocuments(1, pageSize);
        }}
      />

      {/* Chunk Viewer Modal */}
      {selectedDocumentDetail && (
        <DocumentChunkViewer
          document={selectedDocumentDetail}
          onClose={() => setSelectedDocumentDetail(null)}
          onDeleteDocument={(doc) => setDocumentToDelete(doc)}
        />
      )}

      {/* Delete Confirmation Modal */}
      {documentToDelete && (
        <div className="delete-modal-overlay" data-testid="delete-doc-modal-overlay" onClick={() => !isDeleting && setDocumentToDelete(null)}>
          <div
            className="delete-modal-card"
            data-testid="delete-doc-modal-card"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-modal-title"
          >
            <div className="delete-modal-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>

            <h3 id="delete-modal-title" className="delete-modal-title">Xác nhận xóa tài liệu</h3>
            <p className="delete-modal-text">
              Bạn có chắc chắn muốn xóa tài liệu <strong>"{documentToDelete.title}"</strong> (ID: <code style={{ fontSize: '0.8rem' }}>{documentToDelete.id}</code>)?
            </p>
            <p className="delete-modal-warning">
              Toàn bộ nội dung liên quan của tài liệu sẽ bị xóa khỏi bộ nguồn. Dữ liệu lịch sử kiểm chứng vẫn được bảo toàn nguyên vẹn.
            </p>

            <div className="delete-modal-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setDocumentToDelete(null)}
                disabled={isDeleting}
                data-testid="btn-cancel-delete"
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                className="btn-danger-confirm"
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
                data-testid="btn-confirm-delete"
              >
                {isDeleting ? 'Đang xóa...' : 'Xác nhận xóa vĩnh viễn'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
