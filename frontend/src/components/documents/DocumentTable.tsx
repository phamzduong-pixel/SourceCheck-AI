import React, { useState } from 'react';
import { DocumentResponse } from '../../types/document';

interface DocumentTableProps {
  documents: DocumentResponse[];
  onViewDocument: (docId: string) => void;
  onDeleteDocument: (doc: DocumentResponse) => void;
}

export const DocumentTable: React.FC<DocumentTableProps> = ({
  documents,
  onViewDocument,
  onDeleteDocument,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredDocs = documents.filter((doc) =>
    (doc.title || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (doc.doc_type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (doc.publisher || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getDocTypeBadgeClass = (docType: string) => {
    const type = (docType || '').toLowerCase();
    if (type.includes('pdf')) return 'badge-pdf';
    if (type.includes('docx') || type.includes('doc') || type.includes('word')) return 'badge-docx';
    if (type.includes('txt') || type.includes('text') || type.includes('markdown')) return 'badge-txt';
    return 'badge-generic';
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="document-table-wrapper" data-testid="document-table-wrapper">
      {/* Search and Table Toolbar */}
      <div className="document-table-toolbar">
        <div className="table-search-box">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Lọc theo tên, loại file hoặc nguồn phát hành..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            aria-label="Tìm kiếm tài liệu"
            data-testid="document-search-input"
          />
          {searchTerm && (
            <button
              type="button"
              className="clear-search-btn"
              onClick={() => setSearchTerm('')}
              aria-label="Xóa tìm kiếm"
            >
              ✕
            </button>
          )}
        </div>
        <div className="table-stats-count" data-testid="document-table-stats">
          Hiển thị <strong>{filteredDocs.length}</strong> / {documents.length} tài liệu
        </div>
      </div>

      {filteredDocs.length === 0 ? (
        <div className="document-table-empty-filter" data-testid="document-empty-filter">
          <p>Không tìm thấy tài liệu nào khớp với từ khóa "{searchTerm}".</p>
          <button type="button" className="btn-secondary" onClick={() => setSearchTerm('')}>
            Xóa bộ lọc
          </button>
        </div>
      ) : (
        <div className="table-responsive-container">
          <table className="doc-table" data-testid="documents-table">
            <thead>
              <tr>
                <th>Tài liệu</th>
                <th>Loại file</th>
                <th>Trạng thái</th>
                <th>Số đoạn trích</th>
                <th>Ngày tạo</th>
                <th style={{ textAlign: 'right' }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {filteredDocs.map((doc) => (
                <tr key={doc.id} data-testid={`doc-row-${doc.id}`}>
                  <td>
                    <div className="doc-title-cell">
                      <button
                        type="button"
                        className="doc-title-link"
                        onClick={() => onViewDocument(doc.id)}
                        title={doc.title}
                        data-testid={`doc-title-link-${doc.id}`}
                      >
                        {doc.title || 'Tài liệu chưa đặt tên'}
                      </button>
                      {doc.publisher && (
                        <span className="doc-publisher-sub" data-testid={`doc-publisher-${doc.id}`}>
                          Nguồn: {doc.publisher}
                        </span>
                      )}
                      {doc.source_url && (
                        <a
                          href={doc.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="doc-url-sub"
                          data-testid={`doc-url-${doc.id}`}
                        >
                          {doc.source_url} ↗
                        </a>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className={`doc-type-badge ${getDocTypeBadgeClass(doc.doc_type)}`} data-testid={`doc-type-badge-${doc.id}`}>
                      {doc.doc_type ? doc.doc_type.toUpperCase() : 'UNKNOWN'}
                    </span>
                  </td>
                  <td>
                    <span className="doc-status-badge ingested" data-testid={`doc-status-badge-${doc.id}`}>
                      <span className="status-indicator-dot" />
                      Đã nạp
                    </span>
                  </td>
                  <td>
                    <span className="doc-chunks-count" data-testid={`doc-chunk-count-${doc.id}`}>
                      {doc.chunk_count ?? 0}
                    </span>
                  </td>
                  <td className="doc-date-cell">
                    {formatDate(doc.created_at)}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div className="doc-actions-cell">
                      <button
                        type="button"
                        className="btn-table-action view"
                        onClick={() => onViewDocument(doc.id)}
                        title="Xem chi tiết tài liệu"
                        data-testid={`btn-view-doc-${doc.id}`}
                      >
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                        <span>Chi tiết</span>
                      </button>

                      <button
                        type="button"
                        className="btn-table-action delete"
                        onClick={() => onDeleteDocument(doc)}
                        title="Xóa tài liệu khỏi hệ thống"
                        data-testid={`btn-delete-doc-${doc.id}`}
                      >
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          <line x1="10" y1="11" x2="10" y2="17" />
                          <line x1="14" y1="11" x2="14" y2="17" />
                        </svg>
                        <span>Xóa</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
