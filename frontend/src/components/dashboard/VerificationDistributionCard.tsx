import React from 'react';
import { EvaluationSummary, VerificationDistribution } from '../../types/dashboard';
import { TranslationKey } from '../../i18n/types';

interface VerificationDistributionCardProps {
  distribution?: VerificationDistribution | null;
  evaluationSummary?: EvaluationSummary | null;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

export const VerificationDistributionCard: React.FC<VerificationDistributionCardProps> = ({
  distribution,
  evaluationSummary,
  t,
}) => {
  const supported = Number(distribution?.supported ?? 0);
  const partially = Number(distribution?.partially_supported ?? 0);
  const refuted = Number(distribution?.refuted ?? 0);
  const notEnough = Number(distribution?.not_enough_info ?? 0);

  const total = supported + partially + refuted + notEnough;

  const calcPct = (count: number) => {
    if (total === 0) return 0;
    return Math.round((count / total) * 100);
  };

  const supportedPct = calcPct(supported);
  const partiallyPct = calcPct(partially);
  const refutedPct = calcPct(refuted);
  const notEnoughPct = calcPct(notEnough);

  return (
    <div className="dashboard-panel-card" data-testid="verification-distribution-card">
      <div className="panel-card-header">
        <div>
          <h2>{t('dashboard.verificationBreakdownTitle')}</h2>
          <p>{t('dashboard.verificationBreakdownDesc')}</p>
        </div>
      </div>

      <div className="distribution-bars-container" data-testid="distribution-bars">
        {/* 1. Supported */}
        <div className="distribution-item" data-testid="dist-item-supported">
          <div className="distribution-meta">
            <div className="distribution-label-wrapper">
              <span className="distribution-dot supported" />
              <span className="distribution-label-text">{t('dashboard.supported')}</span>
            </div>
            <div className="distribution-count-group">
              <span className="distribution-count" data-testid="dist-count-supported">
                {supported}
              </span>
              <span className="distribution-percentage">({supportedPct}%)</span>
            </div>
          </div>
          <div className="distribution-bar-track">
            <div
              className="distribution-bar-fill supported"
              style={{ width: `${supportedPct}%` }}
              data-testid="dist-bar-supported"
            />
          </div>
        </div>

        {/* 2. Partially Supported */}
        <div className="distribution-item" data-testid="dist-item-partially-supported">
          <div className="distribution-meta">
            <div className="distribution-label-wrapper">
              <span className="distribution-dot partially-supported" />
              <span className="distribution-label-text">{t('dashboard.partiallySupported')}</span>
            </div>
            <div className="distribution-count-group">
              <span className="distribution-count" data-testid="dist-count-partially-supported">
                {partially}
              </span>
              <span className="distribution-percentage">({partiallyPct}%)</span>
            </div>
          </div>
          <div className="distribution-bar-track">
            <div
              className="distribution-bar-fill partially-supported"
              style={{ width: `${partiallyPct}%` }}
              data-testid="dist-bar-partially-supported"
            />
          </div>
        </div>

        {/* 3. Refuted */}
        <div className="distribution-item" data-testid="dist-item-refuted">
          <div className="distribution-meta">
            <div className="distribution-label-wrapper">
              <span className="distribution-dot refuted" />
              <span className="distribution-label-text">{t('dashboard.refuted')}</span>
            </div>
            <div className="distribution-count-group">
              <span className="distribution-count" data-testid="dist-count-refuted">
                {refuted}
              </span>
              <span className="distribution-percentage">({refutedPct}%)</span>
            </div>
          </div>
          <div className="distribution-bar-track">
            <div
              className="distribution-bar-fill refuted"
              style={{ width: `${refutedPct}%` }}
              data-testid="dist-bar-refuted"
            />
          </div>
        </div>

        {/* 4. Not Enough Info */}
        <div className="distribution-item" data-testid="dist-item-not-enough-info">
          <div className="distribution-meta">
            <div className="distribution-label-wrapper">
              <span className="distribution-dot not-enough-info" />
              <span className="distribution-label-text">{t('dashboard.notEnoughInfo')}</span>
            </div>
            <div className="distribution-count-group">
              <span className="distribution-count" data-testid="dist-count-not-enough-info">
                {notEnough}
              </span>
              <span className="distribution-percentage">({notEnoughPct}%)</span>
            </div>
          </div>
          <div className="distribution-bar-track">
            <div
              className="distribution-bar-fill not-enough-info"
              style={{ width: `${notEnoughPct}%` }}
              data-testid="dist-bar-not-enough-info"
            />
          </div>
        </div>
      </div>

      {/* Optional Benchmark Evaluation Summary */}
      {evaluationSummary && (
        <div className="eval-run-banner" data-testid="eval-run-banner">
          <div className="eval-run-header">
            <span>{t('dashboard.evaluationTitle')}</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              {evaluationSummary.run_name} ({evaluationSummary.dataset_name})
            </span>
          </div>
          {evaluationSummary.metrics_summary && (
            <div className="eval-metrics-grid" data-testid="eval-metrics-grid">
              {Object.entries(evaluationSummary.metrics_summary).map(([key, val]) => (
                <div key={key} className="eval-metric-chip">
                  <span className="eval-metric-name">{key}</span>
                  <span className="eval-metric-val">
                    {typeof val === 'number' ? (val < 1 ? `${(val * 100).toFixed(1)}%` : val) : String(val)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
