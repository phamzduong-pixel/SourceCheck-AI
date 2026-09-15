/**
 * EvidenceCoverageCard: Displays the quantitative evidence coverage score and verification verdict counts.
 * Strictly formats and renders data provided by backend without recalculating or computing verdicts.
 */

import React from 'react';

interface EvidenceCoverageCardProps {
  coverage: number;
  status?: string;
  summary?: Record<string, number>;
}

export const EvidenceCoverageCard: React.FC<EvidenceCoverageCardProps> = ({
  coverage,
  status,
  summary,
}) => {
  const percentage = Math.min(100, Math.max(0, Math.round((coverage || 0) * 100)));
  const statusLower = status ? status.toLowerCase() : '';

  return (
    <div className="coverage-card" data-testid="evidence-coverage-card">
      <div className="coverage-header">
        <div className="coverage-title">Độ phủ bằng chứng (Evidence Coverage)</div>
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

      {/* Verification Breakdown Stats */}
      {summary && Object.keys(summary).length > 0 && (
        <div className="coverage-stats" data-testid="coverage-summary-stats">
          <div className="stat-item" data-testid="stat-supported">
            <span className="stat-dot supported" />
            <span>Supported: {summary.SUPPORTED || 0}</span>
          </div>
          <div className="stat-item" data-testid="stat-partially">
            <span className="stat-dot partially" />
            <span>Partially: {summary.PARTIALLY_SUPPORTED || 0}</span>
          </div>
          <div className="stat-item" data-testid="stat-refuted">
            <span className="stat-dot refuted" />
            <span>Refuted: {summary.REFUTED || 0}</span>
          </div>
          <div className="stat-item" data-testid="stat-not-enough-info">
            <span className="stat-dot unverified" />
            <span>Not Enough Info: {summary.NOT_ENOUGH_INFO || 0}</span>
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
        </div>
      )}
    </div>
  );
};
