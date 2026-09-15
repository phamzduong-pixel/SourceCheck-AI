/**
 * ClaimList: Renders atomic factual claims extracted from the synthesized answer,
 * their verification verdict/status from backend, and linked empirical evidence/citations.
 */

import React from 'react';
import { ClaimItem, CitationItem } from '../../types/qa';

interface ClaimListProps {
  claims: ClaimItem[];
  citations?: CitationItem[];
  onCitationClick?: (citation: CitationItem) => void;
}

export const ClaimList: React.FC<ClaimListProps> = ({
  claims,
  citations = [],
  onCitationClick,
}) => {
  if (!claims || claims.length === 0) {
    return null;
  }

  return (
    <div className="claims-section" data-testid="claims-section">
      <div className="claims-section-header">
        <div className="claims-section-title-wrap">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
          <span>Các luận điểm được phân rã (Atomic Claims)</span>
        </div>
        <span className="claims-count-badge">{claims.length} claims</span>
      </div>

      <div className="claims-list">
        {claims.map((claim) => {
          // Find matching citations for this claim from backend response
          const relatedCitations = citations.filter((c) => c.claim_id === claim.claim_id);
          const verdictOrStatus = claim.verdict || claim.status;
          const verdictClass = verdictOrStatus ? verdictOrStatus.toLowerCase() : '';
          const confidence = claim.confidence ?? claim.confidence_score;

          return (
            <div
              key={claim.claim_id}
              className="claim-item-card"
              data-testid={`claim-item-${claim.claim_id}`}
            >
              <div className="claim-item-header">
                <span className="claim-order-badge">#{claim.order}</span>

                <div className="claim-header-text">
                  <p className="claim-text">{claim.text}</p>
                  {claim.context_sentence && (
                    <p className="claim-context">
                      Ngữ cảnh: &ldquo;{claim.context_sentence}&rdquo;
                    </p>
                  )}
                </div>

                {/* Status & Verdict Badges from backend */}
                <div className="claim-meta-badges">
                  {verdictOrStatus && (
                    <span
                      className={`claim-verdict-pill ${verdictClass}`}
                      data-testid={`claim-verdict-${claim.claim_id}`}
                    >
                      ● {verdictOrStatus}
                    </span>
                  )}
                  {typeof confidence === 'number' && (
                    <span
                      className="claim-confidence-pill"
                      data-testid={`claim-confidence-${claim.claim_id}`}
                    >
                      Tin cậy: {Math.round(confidence * 100)}%
                    </span>
                  )}
                  {claim.verifiable === false && (
                    <span
                      className="claim-unverifiable-pill"
                      data-testid={`claim-unverifiable-${claim.claim_id}`}
                    >
                      Không thể kiểm chứng
                    </span>
                  )}
                </div>
              </div>

              {/* Optional explanation from verification */}
              {claim.explanation && (
                <div
                  className="claim-explanation"
                  data-testid={`claim-explanation-${claim.claim_id}`}
                >
                  <span className="explanation-label">Giải thích:</span> {claim.explanation}
                </div>
              )}

              {/* Associated Evidence & Citations */}
              <div
                className="claim-evidence-section"
                data-testid={`claim-evidences-${claim.claim_id}`}
              >
                {relatedCitations.length > 0 ? (
                  <div className="claim-evidence-items">
                    <span className="claim-evidence-label">Bằng chứng liên kết:</span>
                    {relatedCitations.map((cit) => (
                      <div
                        key={cit.citation_id || `${claim.claim_id}-${cit.footnote_index}`}
                        className="claim-evidence-item"
                        data-testid={`claim-evidence-item-${claim.claim_id}-${cit.footnote_index}`}
                      >
                        <button
                          type="button"
                          className="citation-pill claim-evidence-btn"
                          onClick={() => onCitationClick?.(cit)}
                          title={`Xem bằng chứng [${cit.footnote_index}] từ ${cit.source_name}`}
                          aria-label={`Mở bằng chứng [${cit.footnote_index}]`}
                          data-testid={`claim-citation-btn-${claim.claim_id}-${cit.footnote_index}`}
                        >
                          [{cit.footnote_index}]
                        </button>

                        {cit.stance && (
                          <span
                            className={`stance-tag ${cit.stance.toLowerCase()}`}
                            data-testid={`claim-evidence-stance-${claim.claim_id}-${cit.footnote_index}`}
                          >
                            {cit.stance}
                          </span>
                        )}

                        <span className="claim-evidence-source" title={cit.source_name}>
                          {cit.source_name}
                        </span>

                        {cit.quote && (
                          <span className="claim-evidence-quote" title={cit.quote}>
                            &ldquo;{cit.quote}&rdquo;
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div
                    className="claim-no-evidence"
                    data-testid={`claim-no-evidence-${claim.claim_id}`}
                  >
                    <span>Chưa có bằng chứng liên kết</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
