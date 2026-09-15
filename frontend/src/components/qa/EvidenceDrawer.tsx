/**
 * EvidenceDrawer: Slide-in panel displaying detailed grounding evidence and citation provenance.
 * Gracefully handles missing evidence or metadata fields without inventing dummy data.
 */

import React, { useEffect } from 'react';
import { CitationItem, QAEvidenceItem } from '../../types/qa';

interface EvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  citation: CitationItem | null;
  evidence?: QAEvidenceItem | null;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  isOpen,
  onClose,
  citation,
  evidence,
}) => {
  // Listen for Escape key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !citation) {
    return null;
  }

  const stanceLower = (citation.stance || 'context').toLowerCase();
  const sourceTitle =
    citation.source_name ||
    evidence?.source_title ||
    evidence?.publisher ||
    'Chưa có thông tin nguồn';
  const sourceUrl = citation.source_url || evidence?.source_url;

  const relevanceScore =
    typeof citation.relevance_score === 'number'
      ? citation.relevance_score
      : typeof evidence?.score === 'number'
      ? evidence.score
      : null;

  const evidenceId = citation.evidence_id || evidence?.evidence_id;
  const chunkId = evidence?.chunk_id || citation.chunk_id;

  return (
    <>
      {/* Backdrop */}
      <div
        className="evidence-drawer-backdrop"
        onClick={onClose}
        data-testid="evidence-drawer-backdrop"
      />

      {/* Drawer Panel */}
      <aside className="evidence-drawer" data-testid="evidence-drawer">
        {/* Header */}
        <div className="drawer-header">
          <div className="drawer-title-group">
            <span className="citation-pill" style={{ verticalAlign: 'middle' }}>
              [{citation.footnote_index}]
            </span>
            <h3 className="drawer-title">Chi tiết bằng chứng</h3>
          </div>

          <button
            type="button"
            className="drawer-close-btn"
            onClick={onClose}
            aria-label="Close evidence details"
            data-testid="drawer-close-btn"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="drawer-content">
          {/* Stance Indicator (if available) */}
          {citation.stance && (
            <div>
              <div className="drawer-section-label">Lập trường (Stance)</div>
              <span className={`status-pill ${stanceLower}`} data-testid="evidence-stance-badge">
                ● {citation.stance}
              </span>
            </div>
          )}

          {/* Source Box */}
          <div>
            <div className="drawer-section-label">Nguồn tham chiếu</div>
            <div className="drawer-source-box">
              <div className="drawer-source-title" data-testid="evidence-source-title">
                {sourceTitle}
              </div>
              {sourceUrl && (
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="drawer-source-link"
                  data-testid="evidence-source-url"
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

          {/* Verbatim Quote (if available) */}
          {citation.quote && (
            <div>
              <div className="drawer-section-label">Trích dẫn nguyên văn</div>
              <blockquote className="drawer-quote-box" data-testid="evidence-quote">
                "{citation.quote}"
              </blockquote>
            </div>
          )}

          {/* Full Evidence Passage from Chunk (if available) */}
          {evidence?.content && (
            <div>
              <div className="drawer-section-label">Đoạn văn bản đầy đủ (Passage)</div>
              <div className="drawer-passage-box" data-testid="evidence-full-content">
                {evidence.content}
              </div>
            </div>
          )}

          {/* Empty Evidence State if both Quote and Content are missing */}
          {!citation.quote && !evidence?.content && (
            <div className="drawer-empty-state" data-testid="drawer-no-evidence">
              Không có đoạn trích dẫn hoặc nội dung bằng chứng chi tiết từ máy chủ cho trích dẫn này.
            </div>
          )}

          {/* Metadata Grid */}
          <div>
            <div className="drawer-section-label">Thông tin đối soát</div>
            <div className="drawer-meta-grid">
              <div className="meta-item">
                <span className="meta-label">Độ liên quan (Relevance)</span>
                <span className="meta-value" data-testid="evidence-relevance-score">
                  {relevanceScore !== null
                    ? `${(relevanceScore * 100).toFixed(1)}%`
                    : 'N/A'}
                </span>
              </div>

              {evidenceId && (
                <div className="meta-item">
                  <span className="meta-label">Mã bằng chứng</span>
                  <span className="meta-value">{evidenceId}</span>
                </div>
              )}

              {chunkId && (
                <div className="meta-item">
                  <span className="meta-label">Mã chunk</span>
                  <span className="meta-value">{chunkId}</span>
                </div>
              )}

              {evidence?.page_number !== undefined && evidence?.page_number !== null && (
                <div className="meta-item">
                  <span className="meta-label">Trang</span>
                  <span className="meta-value">Trang {evidence.page_number}</span>
                </div>
              )}

              {citation.claim_id && (
                <div className="meta-item">
                  <span className="meta-label">Mã claim</span>
                  <span className="meta-value">{citation.claim_id}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
