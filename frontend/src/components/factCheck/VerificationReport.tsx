/**
 * VerificationReport: Comprehensive Fact-Checking Report component for SourceCheck AI (FE-04).
 * Presents overall verdict, claim counts, verdict distribution, Evidence Coverage,
 * contradiction highlights, and atomic claim-to-evidence traceability.
 */

import React from 'react';
import {
  VerificationResultResponse,
  VerificationEvidenceItem,
  VerifiedClaimItem,
} from '../../types/verification';

interface VerificationReportProps {
  result: VerificationResultResponse;
  onOpenEvidence: (evidence: VerificationEvidenceItem, claimText?: string) => void;
}

export const VerificationReport: React.FC<VerificationReportProps> = ({
  result,
  onOpenEvidence,
}) => {
  const overallVerdict = result.overall_verdict || 'UNVERIFIED';
  const verdictClass = overallVerdict.toLowerCase();
  const claims: VerifiedClaimItem[] = result.claims || [];
  const totalClaims = result.claims_count ?? claims.length;

  // Compute verdict distribution stats from claims
  const supportedCount = claims.filter(
    (c) => (c.verdict || '').toUpperCase() === 'SUPPORTED'
  ).length;
  const partiallyCount = claims.filter(
    (c) => (c.verdict || '').toUpperCase() === 'PARTIALLY_SUPPORTED'
  ).length;
  const refutedCount = claims.filter(
    (c) => (c.verdict || '').toUpperCase() === 'REFUTED'
  ).length;
  const notEnoughInfoCount = claims.filter(
    (c) => (c.verdict || '').toUpperCase() === 'NOT_ENOUGH_INFO' || !c.verdict
  ).length;

  const verifiedClaimsCount = supportedCount + partiallyCount + refutedCount;
  const coverageRatio = totalClaims > 0 ? verifiedClaimsCount / totalClaims : 0;
  const coveragePercentage = Math.min(100, Math.max(0, Math.round(coverageRatio * 100)));

  // Count refuting evidence items
  const totalRefutingEvidences = claims.reduce((acc, claim) => {
    const refutingInClaim = (claim.evidences || []).filter(
      (e) => (e.stance || '').toUpperCase() === 'REFUTES'
    ).length;
    return acc + refutingInClaim;
  }, 0);

  const hasContradictions = refutedCount > 0 || totalRefutingEvidences > 0;

  return (
    <div className="verification-report" data-testid="verification-report">
      {/* 1. Overall Summary & Verdict Card */}
      <div className="overall-verdict-card" data-testid="overall-verdict-card">
        <div className="overall-verdict-header">
          <h2 className="overall-verdict-title">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="m9 12 2 2 4-4" />
            </svg>
            <span>Báo cáo kiểm chứng (Verification Report)</span>
          </h2>

          <span
            className={`verdict-badge ${verdictClass}`}
            data-testid="overall-verdict-badge"
          >
            ● {overallVerdict}
          </span>
        </div>

        {result.summary && (
          <p className="overall-summary" data-testid="overall-summary-text">
            {result.summary}
          </p>
        )}

        {/* Metadata Row */}
        <div className="result-meta-row">
          {result.request_id && (
            <span className="meta-item" data-testid="meta-request-id">
              Mã yêu cầu: {result.request_id}
            </span>
          )}
          {result.status && (
            <span className="meta-item" data-testid="meta-status">
              Trạng thái: {result.status}
            </span>
          )}
          <span className="meta-item" data-testid="meta-claims-count">
            Số nhận định: {totalClaims}
          </span>
          {result.created_at && (
            <span className="meta-item" data-testid="meta-created-at">
              Thời gian: {new Date(result.created_at).toLocaleString('vi-VN')}
            </span>
          )}
        </div>
      </div>

      {/* 2. Evidence Coverage & Verdict Distribution Card */}
      <div className="coverage-card report-overview-card" data-testid="report-coverage-card">
        <div className="coverage-header">
          <div className="coverage-title-group">
            <div className="coverage-title">Độ phủ bằng chứng (Evidence Coverage)</div>
            <p className="coverage-subtitle">
              Tỷ lệ nhận định có bằng chứng đối soát trong cơ sở dữ liệu tri thức (Groundedness)
            </p>
          </div>
          <div className="coverage-percentage" data-testid="report-coverage-percentage">
            {coveragePercentage}%
          </div>
        </div>

        {/* Progress Track & Fill */}
        <div className="coverage-bar-track" aria-label="Evidence coverage percentage bar">
          <div
            className="coverage-bar-fill"
            style={{ width: `${coveragePercentage}%` }}
            data-testid="report-coverage-bar-fill"
          />
        </div>

        {/* Breakdown Stats */}
        <div className="coverage-stats" data-testid="report-verdict-distribution">
          <div className="stat-item stat-verified-ratio" data-testid="report-stat-ratio">
            <span>Đối soát: <strong>{verifiedClaimsCount}/{totalClaims}</strong> nhận định</span>
          </div>
          <div className="stat-item" data-testid="report-stat-supported">
            <span className="stat-dot supported" />
            <span>Supported: {supportedCount}</span>
          </div>
          <div className="stat-item" data-testid="report-stat-partially">
            <span className="stat-dot partially" />
            <span>Partially: {partiallyCount}</span>
          </div>
          <div className="stat-item" data-testid="report-stat-refuted">
            <span className="stat-dot refuted" />
            <span>Refuted: {refutedCount}</span>
          </div>
          <div className="stat-item" data-testid="report-stat-not-enough-info">
            <span className="stat-dot unverified" />
            <span>Not Enough Info: {notEnoughInfoCount}</span>
          </div>
        </div>
      </div>

      {/* 3. Contradiction / Refutation Alert Notice (if present) */}
      {hasContradictions && (
        <div className="contradiction-alert-box" data-testid="contradiction-alert-banner">
          <div className="contradiction-alert-icon">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div className="contradiction-alert-content">
            <h4 className="contradiction-alert-title">
              Phát hiện yếu tố mâu thuẫn / phản bác (Contradictions Detected)
            </h4>
            <p className="contradiction-alert-desc">
              Hệ thống phát hiện {refutedCount > 0 ? `${refutedCount} nhận định bị bác bỏ` : ''}
              {refutedCount > 0 && totalRefutingEvidences > 0 ? ' và ' : ''}
              {totalRefutingEvidences > 0 ? `${totalRefutingEvidences} bằng chứng có lập trường phản bác (REFUTES)` : ''}.
              Vui lòng xem kỹ trích dẫn đối chiếu ở từng mục nhận định bên dưới.
            </p>
          </div>
        </div>
      )}

      {/* 4. Verified Claims Breakdown List */}
      <div className="verified-claims-section" data-testid="verified-claims-section">
        <div className="verified-claims-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
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
            <span>Chi tiết từng nhận định & bằng chứng đối chiếu</span>
          </div>
          <span className="claims-count-tag" data-testid="claims-count-tag">
            {claims.length} claims
          </span>
        </div>

        {claims.length > 0 ? (
          <div className="claims-cards-list" data-testid="verified-claims-list">
            {claims.map((claim, idx) => {
              const claimKey = claim.claim_id || `claim-${idx + 1}`;
              const claimVerdict = claim.verdict || 'UNVERIFIED';
              const claimVerdictClass = claimVerdict.toLowerCase();

              return (
                <div
                  key={claimKey}
                  className="claim-card"
                  data-testid={`verified-claim-${claimKey}`}
                >
                  <div className="claim-card-top">
                    <span className="claim-order-num">#{idx + 1}</span>
                    <p className="claim-card-text" data-testid={`claim-text-${claimKey}`}>
                      {claim.claim_text}
                    </p>
                    <div className="claim-card-badges">
                      <span
                        className={`claim-verdict-tag ${claimVerdictClass}`}
                        data-testid={`claim-verdict-${claimKey}`}
                      >
                        ● {claimVerdict}
                      </span>
                      {typeof claim.confidence_score === 'number' && (
                        <span
                          className="claim-confidence-tag"
                          data-testid={`claim-confidence-${claimKey}`}
                        >
                          Độ tin cậy: {Math.round(claim.confidence_score * 100)}%
                        </span>
                      )}
                    </div>
                  </div>

                  {claim.explanation && (
                    <div
                      className="claim-explanation-box"
                      data-testid={`claim-explanation-${claimKey}`}
                    >
                      <strong>Giải thích:</strong> {claim.explanation}
                    </div>
                  )}

                  {/* Evidence attached to claim */}
                  <div
                    className="claim-evidences-box"
                    data-testid={`claim-evidences-${claimKey}`}
                  >
                    <span className="claim-evidences-title">
                      Bằng chứng đối chiếu ({claim.evidences?.length || 0}):
                    </span>

                    {claim.evidences && claim.evidences.length > 0 ? (
                      <div className="claim-evidences-grouped">
                        {(['SUPPORTS', 'REFUTES', 'NEUTRAL'] as const).map((targetStance) => {
                          const matchingEvidences = claim.evidences.filter(
                            (e) => (e.stance || 'NEUTRAL').toUpperCase() === targetStance
                          );
                          if (matchingEvidences.length === 0) return null;

                          const stanceLabel =
                            targetStance === 'SUPPORTS'
                              ? 'Ủng hộ (Supports)'
                              : targetStance === 'REFUTES'
                              ? 'Mâu thuẫn / Phản bác (Refutes / Contradicts)'
                              : 'Trung lập / Bối cảnh (Neutral)';

                          return (
                            <div
                              key={targetStance}
                              className="stance-group"
                              data-testid={`stance-group-${claimKey}-${targetStance.toLowerCase()}`}
                            >
                              <div className="stance-group-header">
                                <span className={`stance-pill ${targetStance.toLowerCase()}`}>
                                  ● {targetStance}
                                </span>
                                <span>{stanceLabel}</span>
                                <span className="stance-group-count">
                                  {matchingEvidences.length}
                                </span>
                              </div>

                              {matchingEvidences.map((ev) => {
                                const globalEvIdx = claim.evidences.indexOf(ev);
                                const stanceClass = (ev.stance || 'neutral').toLowerCase();

                                return (
                                  <div
                                    key={ev.evidence_id || `ev-${claimKey}-${globalEvIdx}`}
                                    className={`evidence-item-card clickable ${stanceClass}`}
                                    data-testid={`claim-evidence-${claimKey}-${globalEvIdx}`}
                                    onClick={() => onOpenEvidence(ev, claim.claim_text)}
                                  >
                                    <div className="evidence-item-top">
                                      {ev.stance && (
                                        <span
                                          className={`stance-pill ${stanceClass}`}
                                          data-testid={`evidence-stance-${claimKey}-${globalEvIdx}`}
                                        >
                                          {ev.stance}
                                        </span>
                                      )}
                                      <span className="evidence-source-title">{ev.source_title}</span>
                                      {ev.source_url && (
                                        <a
                                          href={ev.source_url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="evidence-source-link"
                                          onClick={(e) => e.stopPropagation()}
                                          data-testid={`evidence-source-url-${claimKey}-${globalEvIdx}`}
                                        >
                                          Xem nguồn &rarr;
                                        </a>
                                      )}
                                    </div>

                                    {(ev.quote || ev.snippet) && (
                                      <p className="evidence-quote-snippet">
                                        &ldquo;{ev.quote || ev.snippet}&rdquo;
                                      </p>
                                    )}

                                    <div className="evidence-actions-bar">
                                      <button
                                        type="button"
                                        className="btn-inspect-evidence"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          onOpenEvidence(ev, claim.claim_text);
                                        }}
                                        data-testid={`btn-inspect-evidence-${claimKey}-${globalEvIdx}`}
                                        aria-label="Xem chi tiết bằng chứng"
                                      >
                                        <span>Xem chi tiết đối chiếu</span>
                                        <span>&rarr;</span>
                                      </button>

                                      {typeof ev.relevance_score === 'number' && ev.relevance_score > 0 && (
                                        <span className="evidence-relevance-score">
                                          Độ khớp: {Math.round(ev.relevance_score * 100)}%
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          );
                        })}

                        {/* Other unclassified stances if backend returns custom stance */}
                        {claim.evidences
                          .filter(
                            (e) =>
                              !['SUPPORTS', 'REFUTES', 'NEUTRAL'].includes(
                                (e.stance || '').toUpperCase()
                              )
                          )
                          .map((ev) => {
                            const globalEvIdx = claim.evidences.indexOf(ev);
                            return (
                              <div
                                key={ev.evidence_id || `ev-other-${claimKey}-${globalEvIdx}`}
                                className="evidence-item-card clickable neutral"
                                data-testid={`claim-evidence-${claimKey}-${globalEvIdx}`}
                                onClick={() => onOpenEvidence(ev, claim.claim_text)}
                              >
                                <div className="evidence-item-top">
                                  <span className="stance-pill neutral">{ev.stance}</span>
                                  <span className="evidence-source-title">{ev.source_title}</span>
                                </div>
                                {(ev.quote || ev.snippet) && (
                                  <p className="evidence-quote-snippet">
                                    &ldquo;{ev.quote || ev.snippet}&rdquo;
                                  </p>
                                )}
                              </div>
                            );
                          })}
                      </div>
                    ) : (
                      <span
                        className="claim-no-evidence-text"
                        data-testid={`claim-no-evidence-${claimKey}`}
                      >
                        Không có bằng chứng trực tiếp đính kèm
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div
            style={{
              textAlign: 'center',
              padding: '1.5rem',
              color: 'var(--color-text-muted)',
              fontSize: '0.9rem',
            }}
            data-testid="empty-claims-notice"
          >
            Không có nhận định độc lập nào được trích xuất từ nội dung đã nhập.
          </div>
        )}
      </div>
    </div>
  );
};
