import React, { useState } from 'react';
import { DocumentDetailResponse, DocumentChunkResponse } from '../../types/document';

interface DocumentChunkViewerProps {
  document: DocumentDetailResponse;
  onClose: () => void;
  onDeleteDocument?: (doc: DocumentDetailResponse) => void;
}

export const DocumentChunkViewer: React.FC<DocumentChunkViewerProps> = ({
  document,
  onClose,
  onDeleteDocument,
}) => {
  const [activeTab, setActiveTab] = useState<'chunks' | 'raw' | 'metadata'>('chunks');
  const [chunkSearch, setChunkSearch] = useState('');
  const [expandedChunkId, setExpandedChunkId] = useState<string | null>(null);
  const [copiedChunkId, setCopiedChunkId] = useState<string | null>(null);

  const chunks = document.chunks || [];
  const filteredChunks = chunks.filter((c) =>
    (c.content || '').toLowerCase().includes(chunkSearch.toLowerCase()) ||
    String(c.chunk_index).includes(chunkSearch)
  );

  const handleCopy = (chunkId: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedChunkId(chunkId);
    setTimeout(() => {
      setCopiedChunkId(null);
    }, 2000);
  };

  const toggleChunkExpand = (chunkId: string) => {
    setExpandedChunkId(expandedChunkId === chunkId ? null : chunkId);
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString('vi-VN');
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="chunk-viewer-overlay" data-testid="chunk-viewer-overlay" onClick={onClose}>
      <div
        className="chunk-viewer-modal"
        data-testid="chunk-viewer-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="chunk-viewer-title"
      >
        {/* Modal Header */}
        <div className="chunk-viewer-header">
          <div className="viewer-title-area">
            <span className="viewer-badge-doc">Tài liệu</span>
            <h2 id="chunk-viewer-title" className="viewer-title" data-testid="viewer-doc-title">
              {document.title || 'Chi tiết tài liệu'}
            </h2>
          </div>
          <div className="viewer-header-actions">
            {onDeleteDocument && (
              <button
                type="button"
                className="btn-viewer-delete"
                onClick={() => onDeleteDocument(document)}
                title="Xóa tài liệu này"
                data-testid="btn-viewer-delete-doc"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
                <span>Xóa tài liệu</span>
              </button>
            )}
            <button
              type="button"
              className="btn-viewer-close"
              onClick={onClose}
              aria-label="Đóng"
              data-testid="btn-close-chunk-viewer"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Quick Meta Stats Row */}
        <div className="viewer-stats-strip" data-testid="viewer-stats-strip">
          <div className="viewer-stat-item">
            <span className="stat-label">Loại tài liệu:</span>
            <span className="stat-value" data-testid="viewer-doc-type">
              {document.doc_type ? document.doc_type.toUpperCase() : 'UNKNOWN'}
            </span>
          </div>
          <div className="viewer-stat-item">
            <span className="stat-label">Tổng số đoạn trích:</span>
            <span className="stat-value highlight" data-testid="viewer-chunks-count">
              {chunks.length} đoạn trích
            </span>
          </div>
          <div className="viewer-stat-item">
            <span className="stat-label">Trạng thái:</span>
            <span className="stat-value status-ready" data-testid="viewer-ingestion-status">
              ● Sẵn sàng sử dụng làm nguồn
            </span>
          </div>
          <div className="viewer-stat-item">
            <span className="stat-label">Ngày tạo:</span>
            <span className="stat-value" data-testid="viewer-created-at">
              {formatDate(document.created_at)}
            </span>
          </div>
          {document.source_url && (
            <div className="viewer-stat-item">
              <span className="stat-label">Nguồn:</span>
              <a
                href={document.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="stat-link"
                data-testid="viewer-source-url"
              >
                Mở liên kết ↗
              </a>
            </div>
          )}
        </div>

        {/* Navigation Tabs */}
        <div className="viewer-tabs" role="tablist">
          <button
            type="button"
            className={`viewer-tab-btn ${activeTab === 'chunks' ? 'active' : ''}`}
            onClick={() => setActiveTab('chunks')}
            role="tab"
            aria-selected={activeTab === 'chunks'}
            data-testid="tab-view-chunks"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
            <span>Các đoạn trích ({chunks.length})</span>
          </button>
          <button
            type="button"
            className={`viewer-tab-btn ${activeTab === 'raw' ? 'active' : ''}`}
            onClick={() => setActiveTab('raw')}
            role="tab"
            aria-selected={activeTab === 'raw'}
            data-testid="tab-view-raw"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span>Nội dung đầy đủ</span>
          </button>
          <button
            type="button"
            className={`viewer-tab-btn ${activeTab === 'metadata' ? 'active' : ''}`}
            onClick={() => setActiveTab('metadata')}
            role="tab"
            aria-selected={activeTab === 'metadata'}
            data-testid="tab-view-metadata"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            <span>Thông tin tài liệu & Cấu hình</span>
          </button>
        </div>

        {/* Modal Body Content */}
        <div className="chunk-viewer-body">
          {/* TAB 1: CHUNKS ACCORDION LIST */}
          {activeTab === 'chunks' && (
            <div className="chunks-tab-content">
              <div className="chunks-search-row">
                <input
                  type="text"
                  placeholder="Lọc đoạn trích theo nội dung..."
                  value={chunkSearch}
                  onChange={(e) => setChunkSearch(e.target.value)}
                  className="chunks-filter-input"
                  data-testid="chunk-filter-input"
                />
                <span className="chunks-filtered-count">
                  {filteredChunks.length} / {chunks.length} đoạn trích
                </span>
              </div>

              {filteredChunks.length === 0 ? (
                <div className="no-chunks-notice" data-testid="no-chunks-match">
                  Không tìm thấy đoạn trích phù hợp.
                </div>
              ) : (
                <div className="chunks-list" data-testid="chunks-accordion-list">
                  {filteredChunks.map((chunk: DocumentChunkResponse) => {
                    const isExpanded = expandedChunkId === chunk.id;
                    const charCount = (chunk.content || '').length;
                    const meta = chunk.chunk_metadata || {};

                    return (
                      <div
                        key={chunk.id}
                        className={`chunk-item-card ${isExpanded ? 'expanded' : ''}`}
                        data-testid={`chunk-card-${chunk.chunk_index}`}
                      >
                        <div
                          className="chunk-card-header"
                          onClick={() => toggleChunkExpand(chunk.id)}
                          role="button"
                          tabIndex={0}
                          aria-expanded={isExpanded}
                          data-testid={`chunk-header-${chunk.chunk_index}`}
                        >
                          <div className="chunk-header-left">
                            <span className="chunk-index-badge" data-testid={`chunk-index-${chunk.chunk_index}`}>
                              Đoạn trích #{chunk.chunk_index}
                            </span>
                            <span className="chunk-char-count">{charCount} ký tự</span>
                            {meta.page_number !== undefined && (
                              <span className="chunk-meta-pill">Trang {meta.page_number}</span>
                            )}
                          </div>
                          <div className="chunk-header-right">
                            <button
                              type="button"
                              className="btn-chunk-copy"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCopy(chunk.id, chunk.content);
                              }}
                              data-testid={`btn-copy-chunk-${chunk.chunk_index}`}
                              title="Sao chép nội dung chunk"
                            >
                              {copiedChunkId === chunk.id ? '✓ Đã chép' : 'Sao chép'}
                            </button>
                            <span className="chunk-expand-icon">{isExpanded ? '▲' : '▼'}</span>
                          </div>
                        </div>

                        <div className="chunk-card-body">
                          <p className="chunk-text-content" data-testid={`chunk-content-${chunk.chunk_index}`}>
                            {chunk.content}
                          </p>

                          {meta && Object.keys(meta).length > 0 && (
                            <div className="chunk-metadata-box" data-testid={`chunk-meta-${chunk.chunk_index}`}>
                              <strong>Đoạn trích Thông tin tài liệu:</strong>
                              <pre>{JSON.stringify(meta, null, 2)}</pre>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: RAW CONTENT */}
          {activeTab === 'raw' && (
            <div className="raw-content-tab" data-testid="raw-content-container">
              {document.raw_content ? (
                <pre className="raw-content-pre" data-testid="raw-content-text">
                  {document.raw_content}
                </pre>
              ) : (
                <div className="no-chunks-notice" data-testid="no-raw-content">
                  Không có nội dung thô (Nội dung đầy đủ) được lưu trữ cho tài liệu này.
                </div>
              )}
            </div>
          )}

          {/* TAB 3: METADATA */}
          {activeTab === 'metadata' && (
            <div className="metadata-tab" data-testid="metadata-tab-container">
              <div className="metadata-grid">
                <div className="meta-field">
                  <span className="meta-key">Mã tài liệu:</span>
                  <code className="meta-val-code" data-testid="meta-val-id">{document.id}</code>
                </div>
                <div className="meta-field">
                  <span className="meta-key">Tiêu đề (Title):</span>
                  <span className="meta-val">{document.title}</span>
                </div>
                <div className="meta-field">
                  <span className="meta-key">Loại định dạng:</span>
                  <span className="meta-val">{document.doc_type}</span>
                </div>
                <div className="meta-field">
                  <span className="meta-key">Nguồn / Tác giả:</span>
                  <span className="meta-val">{document.publisher || 'Không có'}</span>
                </div>
                <div className="meta-field">
                  <span className="meta-key">Đường dẫn nguồn:</span>
                  <span className="meta-val">{document.source_url || 'Không có'}</span>
                </div>
                <div className="meta-field">
                  <span className="meta-key">Thời gian tạo:</span>
                  <span className="meta-val">{document.created_at}</span>
                </div>
                {document.updated_at && (
                  <div className="meta-field">
                    <span className="meta-key">Cập nhật lần cuối:</span>
                    <span className="meta-val">{document.updated_at}</span>
                  </div>
                )}
              </div>

              {document.doc_metadata && Object.keys(document.doc_metadata).length > 0 && (
                <div className="raw-metadata-json-section">
                  <h4>Thông tin bổ sung</h4>
                  <pre className="raw-content-pre" data-testid="doc-custom-metadata-pre">
                    {JSON.stringify(document.doc_metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="chunk-viewer-footer">
          <button type="button" className="btn-secondary" onClick={onClose} data-testid="btn-viewer-footer-close">
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
};
