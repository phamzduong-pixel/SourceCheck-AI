/**
 * EvidenceCoverageCard: Displays the quantitative evidence coverage score and verification verdict counts.
 * Strictly formats and renders data provided by backend without recalculating or computing verdicts.
 */

import React from 'react';

interface EvidenceCoverageCardProps {
  coverage: number;
  status?: string;
  summary?: Record<string, number>;
  totalClaims?: number;
}

export const EvidenceCoverageCard: React.FC<EvidenceCoverageCardProps> = ({
  coverage,
  status,
  summary,
  totalClaims,
}) => {
  const percentage = Math.min(100, Math.max(0, Math.round((coverage || 0) * 100)));
  const statusLower = status ? status.toLowerCase() : '';

  // Calculate verified count and total claims from summary if available
  const supportedCount = summary?.SUPPORTED || 0;
  const partiallyCount = summary?.PARTIALLY_SUPPORTED || 0;
  const refutedCount = summary?.REFUTED || 0;
  const notEnoughInfoCount = summary?.NOT_ENOUGH_INFO || 0;
  const verifiedCount = supportedCount + partiallyCount + refutedCount;
  const computedTotal = totalClaims ?? (supportedCount + partiallyCount + refutedCount + notEnoughInfoCount);

  return (
    <div className="coverage-card" data-testid="evidence-coverage-card">
      <div className="coverage-header">
        <div className="coverage-title-group">
          <div className="coverage-title">Độ phủ bằng chứng (Evidence Coverage)</div>
          <p className="coverage-subtitle">
            Tỷ lệ các luận điểm có tài liệu đối soát trong cơ sở tri thức (Groundedness)
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {status && (
            <span className={`status-pill ${statusLower}`} data-testid="coverage-status-pill">
              ● {status}
            </span>
          )}
          <div className="coverage-percentage" data-testid="coverage-percentage-value">
            {percentage}%
          </div>
        </div>
      </div>

      {/* Progress Track & Fill */}
      <div className="coverage-bar-track" aria-label="Evidence coverage percentage bar">
        <div
          className="coverage-bar-fill"
          style={{ width: `${percentage}%` }}
          data-testid="coverage-bar-fill"
        />
      </div>

      {/* Claims Verified Ratio & Stats */}
      <div className="coverage-stats" data-testid="coverage-summary-stats">
        {computedTotal > 0 && (
          <div className="stat-item stat-verified-ratio" data-testid="stat-verified-ratio">
            <span>Đối soát: <strong>{verifiedCount}/{computedTotal}</strong> claims</span>
          </div>
        )}
        {summary && (
          <>
            <div className="stat-item" data-testid="stat-supported">
              <span className="stat-dot supported" />
              <span>Supported: {supportedCount}</span>
            </div>
            <div className="stat-item" data-testid="stat-partially">
              <span className="stat-dot partially" />
              <span>Partially: {partiallyCount}</span>
            </div>
            <div className="stat-item" data-testid="stat-refuted">
              <span className="stat-dot refuted" />
              <span>Refuted: {refutedCount}</span>
            </div>
            <div className="stat-item" data-testid="stat-not-enough-info">
              <span className="stat-dot unverified" />
              <span>Not Enough Info: {notEnoughInfoCount}</span>
            </div>
            {/* Support any additional summary verdict keys returned by backend */}
            {Object.entries(summary)
              .filter(([k]) => !['SUPPORTED', 'PARTIALLY_SUPPORTED', 'REFUTED', 'NOT_ENOUGH_INFO'].includes(k))
              .map(([k, count]) => (
                <div key={k} className="stat-item" data-testid={`stat-${k.toLowerCase()}`}>
                  <span className="stat-dot unverified" />
                  <span>{k}: {count}</span>
                </div>
              ))}
          </>
        )}
      </div>
    </div>
  );
};
