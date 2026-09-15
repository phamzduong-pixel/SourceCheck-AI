/**
 * FactCheckEvidenceDrawer: Slide-in panel displaying detailed verification evidence and stance.
 * Gracefully handles missing evidence or optional metadata fields without inventing dummy data.
 */

import React, { useEffect } from 'react';
import { VerificationEvidenceItem } from '../../types/verification';

interface FactCheckEvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  evidence: VerificationEvidenceItem | null;
  claimText?: string;
}

export const FactCheckEvidenceDrawer: React.FC<FactCheckEvidenceDrawerProps> = ({
  isOpen,
  onClose,
  evidence,
  claimText,
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

  if (!isOpen || !evidence) {
    return null;
  }

  const stanceLower = (evidence.stance || 'neutral').toLowerCase();
  const sourceTitle = evidence.source_title || evidence.publisher || 'Chưa có thông tin nguồn';
  const sourceUrl = evidence.source_url;

  return (
    <>
      {/* Backdrop */}
      <div
        className="evidence-drawer-backdrop"
        onClick={onClose}
        data-testid="fc-evidence-drawer-backdrop"
      />

      {/* Drawer Panel */}
      <aside className="evidence-drawer" data-testid="fc-evidence-drawer">
        {/* Header */}
        <div className="drawer-header">
          <div className="drawer-title-group">
            <span
              className={`stance-pill ${stanceLower}`}
              style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem' }}
              data-testid="fc-drawer-header-stance"
            >
              ● {evidence.stance}
            </span>
            <h3 className="drawer-title">Chi tiết bằng chứng đối chiếu</h3>
          </div>

          <button
            type="button"
            className="drawer-close-btn"
            onClick={onClose}
            aria-label="Đóng bảng chi tiết bằng chứng"
            data-testid="fc-drawer-close-btn"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="drawer-content">
          {/* Claim Context (if provided) */}
          {claimText && (
            <div>
              <div className="drawer-section-label">Nhận định đối soát</div>
              <div className="claim-explanation-box" style={{ margin: 0 }} data-testid="fc-drawer-claim-text">
                {claimText}
              </div>
            </div>
          )}

          {/* Stance Indicator & Meaning */}
          <div>
            <div className="drawer-section-label">Quan hệ & Lập trường (Stance)</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
              <span className={`stance-pill ${stanceLower}`} data-testid="fc-drawer-stance-badge">
                ● {evidence.stance}
              </span>
              <span style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)' }}>
                {evidence.stance === 'SUPPORTS' && 'Bằng chứng này ủng hộ/xác nhận nhận định.'}
                {evidence.stance === 'REFUTES' && 'Bằng chứng này phản bác/mâu thuẫn với nhận định.'}
                {evidence.stance === 'NEUTRAL' && 'Bằng chứng cung cấp thông tin trung lập hoặc ngữ cảnh liên quan.'}
              </span>
            </div>
          </div>

          {/* Source Box */}
          <div>
            <div className="drawer-section-label">Nguồn tham chiếu</div>
            <div className="drawer-source-box">
              <div className="drawer-source-title" data-testid="fc-drawer-source-title">
                {sourceTitle}
              </div>
              {evidence.publisher && (
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '0.35rem' }} data-testid="fc-drawer-publisher">
                  Đơn vị xuất bản: <strong>{evidence.publisher}</strong>
                </div>
              )}
              {sourceUrl && (
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="drawer-source-link"
                  data-testid="fc-drawer-source-url"
                >
                  <span>{sourceUrl}</span>
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                  </svg>
                </a>
              )}
            </div>
          </div>

          {/* Verbatim Quote (if available) */}
          {evidence.quote && (
            <div>
              <div className="drawer-section-label">Trích dẫn nguyên văn</div>
              <blockquote
                className="drawer-quote-box"
                style={{
                  backgroundColor:
                    evidence.stance === 'REFUTES'
                      ? 'var(--color-danger-bg)'
                      : evidence.stance === 'SUPPORTS'
                      ? 'var(--color-success-bg)'
                      : 'var(--color-neutral-bg)',
                  borderColor:
                    evidence.stance === 'REFUTES'
                      ? 'var(--color-status-offline)'
                      : evidence.stance === 'SUPPORTS'
                      ? 'var(--color-status-ready)'
                      : 'var(--color-border)',
                  color:
                    evidence.stance === 'REFUTES'
                      ? 'var(--color-danger-text)'
                      : evidence.stance === 'SUPPORTS'
                      ? 'var(--color-success-text)'
                      : 'var(--color-text-primary)',
                }}
                data-testid="fc-drawer-quote"
              >
                &ldquo;{evidence.quote}&rdquo;
              </blockquote>
            </div>
          )}

          {/* Snippet / Passage */}
          {evidence.snippet && (
            <div>
              <div className="drawer-section-label">Đoạn văn trích xuất (Snippet)</div>
              <div className="drawer-passage-box" data-testid="fc-drawer-snippet">
                {evidence.snippet}
              </div>
            </div>
          )}

          {/* Fallback if both quote and snippet are absent */}
          {!evidence.quote && !evidence.snippet && (
            <div className="drawer-empty-state" data-testid="fc-drawer-no-content">
              Không có đoạn trích dẫn hoặc nội dung chi tiết kèm theo từ máy chủ cho bằng chứng này.
            </div>
          )}

          {/* Metadata Grid */}
          <div>
            <div className="drawer-section-label">Thông tin đối soát</div>
            <div className="drawer-meta-grid">
              {typeof evidence.relevance_score === 'number' && evidence.relevance_score > 0 && (
                <div className="meta-item">
                  <span className="meta-label">Độ tương quan (Relevance)</span>
                  <span className="meta-value" data-testid="fc-drawer-relevance">
                    {Math.round(evidence.relevance_score * 100)}%
                  </span>
                </div>
              )}

              {evidence.evidence_id && (
                <div className="meta-item">
                  <span className="meta-label">Mã bằng chứng</span>
                  <span className="meta-value" data-testid="fc-drawer-evidence-id">
                    {evidence.evidence_id}
                  </span>
                </div>
              )}

              <div className="meta-item">
                <span className="meta-label">Lập trường xác nhận</span>
                <span className="meta-value">{evidence.stance}</span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
