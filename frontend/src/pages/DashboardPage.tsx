/**
 * DashboardPage: Overview landing page of the authenticated SourceCheck AI workspace.
 * Displays real-time system metrics, verification distribution, recent activity timeline,
 * benchmark evaluation summaries, and quick navigation actions.
 */

import React, { useEffect, useState } from 'react';
import { useAIPreferences } from '../hooks/useAIPreferences';
import { dashboardService } from '../services/dashboard';
import { DashboardStats } from '../types/dashboard';
import { ApiClientError } from '../services/apiClient';
import {
  DashboardSummaryCards,
  VerificationDistributionCard,
  RecentActivityFeed,
  QuickActionsGrid,
} from '../components/dashboard';
import '../styles/dashboard.css';

export const DashboardPage: React.FC = () => {
  const { t } = useAIPreferences();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async (isManualRefresh = false) => {
    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const data = await dashboardService.getStats();
      setStats(data);
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError(t('dashboard.errorTitle'));
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const isSystemEmpty =
    stats &&
    (stats.total_documents ?? 0) === 0 &&
    (stats.total_questions ?? 0) === 0 &&
    (stats.total_verifications ?? 0) === 0 &&
    (stats.total_conversations ?? 0) === 0;

  return (
    <div className="dashboard-page-container" data-testid="dashboard-page">
      {/* Top Header & Actions */}
      <div className="dashboard-header-row" data-testid="dashboard-header">
        <div className="dashboard-hero-title-group">
          <span className="dashboard-hero-badge">{t('dashboard.heroBadge')}</span>
          <h1>{t('dashboard.heroTitle')}</h1>
          <p>{t('dashboard.heroDescription')}</p>
        </div>
        <div className="dashboard-actions-group">
          <button
            type="button"
            className="btn-dashboard-refresh"
            onClick={() => fetchStats(true)}
            disabled={isLoading || isRefreshing}
            data-testid="btn-dashboard-refresh"
            title={t('dashboard.refresh')}
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={isRefreshing ? 'status-dot checking' : ''}
            >
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
            <span>{isRefreshing ? t('dashboard.refreshing') : t('dashboard.refresh')}</span>
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="dashboard-error-banner" data-testid="dashboard-error-banner">
          <div>
            <strong>{t('dashboard.errorTitle')}: </strong>
            <span>{error}</span>
          </div>
          <button
            type="button"
            className="btn-error-retry"
            onClick={() => fetchStats(false)}
            data-testid="btn-dashboard-retry"
          >
            {t('dashboard.retry')}
          </button>
        </div>
      )}

      {/* Loading Skeletons */}
      {isLoading && !stats && (
        <div data-testid="dashboard-loading-skeleton" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="summary-cards-grid">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="dashboard-skeleton-card" />
            ))}
          </div>
          <div className="dashboard-main-grid">
            <div className="dashboard-skeleton-panel" />
            <div className="dashboard-skeleton-panel" />
          </div>
        </div>
      )}

      {/* Populated Dashboard Metrics */}
      {stats && (
        <>
          {/* Empty System Notice */}
          {isSystemEmpty && (
            <div
              style={{
                padding: '0.85rem 1.25rem',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--color-bg-muted)',
                border: '1px solid var(--color-border)',
                fontSize: '0.875rem',
                color: 'var(--color-text-secondary)',
              }}
              data-testid="dashboard-empty-notice"
            >
              ℹ️ {t('dashboard.emptyNotice')}
            </div>
          )}

          {/* 1. Summary Cards */}
          <DashboardSummaryCards stats={stats} t={t} />

          {/* 2. Main Two-Column Panel: Verification Breakdown + Recent Activities */}
          <div className="dashboard-main-grid">
            <VerificationDistributionCard
              distribution={stats.verification_distribution}
              evaluationSummary={stats.evaluation_summary}
              t={t}
            />
            <RecentActivityFeed activities={stats.recent_activity || []} t={t} />
          </div>
        </>
      )}

      {/* 3. Quick Actions Feature Grid (Always accessible) */}
      <div style={{ marginTop: '0.5rem' }}>
        <h2 style={{ fontSize: '1.15rem', fontWeight: 650, margin: '0 0 1rem 0' }}>
          {t('dashboard.quickActionsTitle')}
        </h2>
        <QuickActionsGrid t={t} />
      </div>
    </div>
  );
};
