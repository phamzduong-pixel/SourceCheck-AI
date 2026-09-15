/**
 * RetrievalDetailsDrawer: Detailed inspector panel for a single retrieval hit.
 * Displays the complete retrieval pipeline: Query -> Vector -> BM25 -> RRF -> Reranker -> Final Rank.
 * Gracefully displays only the scores and provenance fields provided by the backend.
 */

import React, { useEffect } from 'react';
import { SearchHit } from '../../types/search';
import { useAIPreferences } from '../../hooks/useAIPreferences';

interface RetrievalDetailsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  hit: SearchHit | null;
  query?: string;
}

export const RetrievalDetailsDrawer: React.FC<RetrievalDetailsDrawerProps> = ({
  isOpen,
  onClose,
  hit,
  query,
}) => {
  const { t } = useAIPreferences();
  // Listen for Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !hit) {
    return null;
  }

  // Extract source information
  const sourceTitle =
    hit.source_title ||
    (hit.source && typeof hit.source === 'object' && 'title' in hit.source
      ? String(hit.source.title)
      : null) ||
    'Tài liệu không có tiêu đề';

  const sourceUrl =
    hit.source_url ||
    (hit.source && typeof hit.source === 'object' && 'url' in hit.source
      ? String(hit.source.url)
      : null);

  const publisher =
    hit.publisher ||
    (hit.source && typeof hit.source === 'object' && 'publisher' in hit.source
      ? String(hit.source.publisher)
      : null);

  const pageNumber =
    hit.page_number !== undefined && hit.page_number !== null
      ? hit.page_number
      : hit.metadata?.page_number;

  const documentId =
    hit.document_id ||
    (hit.source && typeof hit.source === 'object' && 'document_id' in hit.source
      ? String(hit.source.document_id)
      : null);

  return (
    <>
      {/* Backdrop */}
      <div
        className="retrieval-drawer-backdrop"
        onClick={onClose}
        data-testid="retrieval-drawer-backdrop"
      />

      {/* Drawer Panel */}
      <aside className="retrieval-drawer" data-testid="retrieval-details-drawer">
        {/* Header */}
        <div className="retrieval-drawer-header">
          <div className="drawer-title-group">
            {hit.rank !== undefined && hit.rank !== null && (
              <span className="rank-badge primary" data-testid="drawer-hit-rank">
                #{hit.rank}
              </span>
            )}
            <h3 className="drawer-title">Chi tiết Retrieval & Pipeline</h3>
          </div>

          <button
            type="button"
            className="drawer-close-btn"
            onClick={onClose}
aria-label={t('common.closeDetails')}
            data-testid="btn-close-retrieval-drawer"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Content Body */}
        <div className="retrieval-drawer-content">
          {/* Query context */}
          {query && (
            <div className="drawer-section">
              <div className="drawer-section-label">Câu truy vấn (Search Query)</div>
              <div className="drawer-query-box" data-testid="drawer-query-box">
                "{query}"
              </div>
            </div>
          )}

          {/* Pipeline Breakdown Step-by-Step */}
          <div className="drawer-section">
            <div className="drawer-section-label">Tiến trình xếp hạng (Pipeline Breakdown)</div>
            <div className="pipeline-timeline" data-testid="pipeline-timeline">
              {/* Step 1: Vector Search */}
              <div className="pipeline-step" data-testid="step-vector">
                <div className="step-icon vector-icon">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                </div>
                <div className="step-body">
                  <div className="step-title">Dense Vector Search (pgvector)</div>
                  <div className="step-desc">Truy xuất ngữ nghĩa qua cosine similarity</div>
                  <div className="step-metrics">
                    {hit.vector_score !== undefined && hit.vector_score !== null ? (
                      <>
                        <span className="metric-tag" data-testid="metric-vector-score">
                          Score: <strong>{Number(hit.vector_score).toFixed(4)}</strong>
                        </span>
                        {hit.vector_rank !== undefined && hit.vector_rank !== null && (
                          <span className="metric-tag" data-testid="metric-vector-rank">
                            Vector Rank: <strong>#{hit.vector_rank}</strong>
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="metric-muted">Không kích hoạt trong truy vấn này</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Step 2: BM25 Lexical Match */}
              <div className="pipeline-step" data-testid="step-bm25">
                <div className="step-icon bm25-icon">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                  </svg>
                </div>
                <div className="step-body">
                  <div className="step-title">BM25 Lexical Search (Từ khóa chính xác)</div>
                  <div className="step-desc">Khớp từ khóa và thực thể qua tần suất thuật ngữ</div>
                  <div className="step-metrics">
                    {hit.bm25_score !== undefined && hit.bm25_score !== null ? (
                      <>
                        <span className="metric-tag" data-testid="metric-bm25-score">
                          Score: <strong>{Number(hit.bm25_score).toFixed(4)}</strong>
                        </span>
                        {hit.bm25_rank !== undefined && hit.bm25_rank !== null && (
                          <span className="metric-tag" data-testid="metric-bm25-rank">
                            BM25 Rank: <strong>#{hit.bm25_rank}</strong>
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="metric-muted">Không kích hoạt trong truy vấn này</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Step 3: RRF Fusion */}
              <div className="pipeline-step" data-testid="step-rrf">
                <div className="step-icon rrf-icon">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                    <polyline points="17 6 23 6 23 12" />
                  </svg>
                </div>
                <div className="step-body">
                  <div className="step-title">Reciprocal Rank Fusion (RRF)</div>
                  <div className="step-desc">Hợp nhất xếp hạng đa nguồn không phụ thuộc scale điểm</div>
                  <div className="step-metrics">
                    {hit.rrf_score !== undefined && hit.rrf_score !== null ? (
                      <span className="metric-tag highlight" data-testid="metric-rrf-score">
                        RRF Score: <strong>{Number(hit.rrf_score).toFixed(5)}</strong>
                      </span>
                    ) : (
                      <span className="metric-muted">Không áp dụng (truy vấn đơn nguồn)</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Step 4: Cross-Encoder Reranker */}
              <div className="pipeline-step" data-testid="step-rerank">
                <div className="step-icon rerank-icon">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                  </svg>
                </div>
                <div className="step-body">
                  <div className="step-title">Cross-Encoder Reranker</div>
                  <div className="step-desc">Đánh giá tương tác chéo query-passage ở cấp độ câu</div>
                  <div className="step-metrics">
                    {hit.rerank_score !== undefined && hit.rerank_score !== null ? (
                      <span className="metric-tag rerank" data-testid="metric-rerank-score">
                        Rerank Score: <strong>{Number(hit.rerank_score).toFixed(4)}</strong>
                      </span>
                    ) : (
                      <span className="metric-muted">Tắt reranking hoặc không áp dụng</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Step 5: Final Verdict / Rank */}
              <div className="pipeline-step final" data-testid="step-final">
                <div className="step-icon final-icon">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <div className="step-body">
                  <div className="step-title">Thứ hạng cuối cùng (Final Rank)</div>
                  <div className="step-metrics">
                    <span className="metric-tag final-badge" data-testid="metric-final-rank">
                      Rank: <strong>#{hit.rank ?? 1}</strong>
                    </span>
                    <span className="metric-tag final-score" data-testid="metric-final-score">
                      Final Score: <strong>{Number(hit.score).toFixed(4)}</strong>
                    </span>
                    {hit.retriever_type && (
                      <span className="metric-tag retriever-badge" data-testid="metric-retriever-type">
                        Type: <strong>{hit.retriever_type}</strong>
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Chunk Content Passage */}
          <div className="drawer-section">
            <div className="drawer-section-label">Nội dung đoạn trích (Chunk Passage)</div>
            <div className="drawer-passage-box" data-testid="drawer-chunk-content">
              {hit.content}
            </div>
          </div>

          {/* Source & Provenance Box */}
          <div className="drawer-section">
            <div className="drawer-section-label">Nguồn tham chiếu & Xuất bản</div>
            <div className="drawer-source-box">
              <div className="drawer-source-title" data-testid="drawer-source-title">
                {sourceTitle}
              </div>

              {sourceUrl && (
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="drawer-source-link"
                  data-testid="drawer-source-url"
                >
                  <span>{sourceUrl}</span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                  </svg>
                </a>
              )}
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="drawer-section">
            <div className="drawer-section-label">Thông tin định danh & Metadata</div>
            <div className="drawer-meta-grid">
              <div className="meta-item">
                <span className="meta-label">Chunk ID</span>
                <span className="meta-value code-value" data-testid="drawer-chunk-id">
                  {hit.chunk_id}
                </span>
              </div>

              {documentId && (
                <div className="meta-item">
                  <span className="meta-label">Document ID</span>
                  <span className="meta-value code-value" data-testid="drawer-document-id">
                    {documentId}
                  </span>
                </div>
              )}

              {publisher && (
                <div className="meta-item">
                  <span className="meta-label">Nhà xuất bản / Cơ quan</span>
                  <span className="meta-value" data-testid="drawer-publisher">
                    {publisher}
                  </span>
                </div>
              )}

              {pageNumber !== undefined && pageNumber !== null && (
                <div className="meta-item">
                  <span className="meta-label">Trang</span>
                  <span className="meta-value" data-testid="drawer-page-number">
                    Trang {pageNumber}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Raw Metadata JSON (if available) */}
          {hit.metadata && Object.keys(hit.metadata).length > 0 && (
            <div className="drawer-section">
              <div className="drawer-section-label">Metadata mở rộng (Raw JSON)</div>
              <pre className="drawer-json-block" data-testid="drawer-metadata-json">
                {JSON.stringify(hit.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
