/**
 * SystemHealthCard: Real-time operational monitoring panel displaying overall
 * system health and the status of critical dependencies (Postgres, pgvector, LLM, Embedding, Reranker).
 */

import React from 'react';
import { SystemHealthResponse, HealthStatus, DependencyHealth } from '../../types/dashboard';
import { TranslationKey } from '../../i18n/types';

interface SystemHealthCardProps {
  health: SystemHealthResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

export const SystemHealthCard: React.FC<SystemHealthCardProps> = ({
  health,
  isLoading,
  onRefresh,
  t,
}) => {
  const getStatusBadge = (status: HealthStatus) => {
    switch (status) {
      case 'healthy':
        return {
          label: t('dashboard.healthStatusHealthy'),
          className: 'health-badge-healthy',
          dotColor: 'var(--color-success, #16a34a)',
        };
      case 'degraded':
        return {
          label: t('dashboard.healthStatusDegraded'),
          className: 'health-badge-degraded',
          dotColor: 'var(--color-warning, #d97706)',
        };
      case 'unavailable':
        return {
          label: t('dashboard.healthStatusUnavailable'),
          className: 'health-badge-unavailable',
          dotColor: 'var(--color-danger, #dc2626)',
        };
      default:
        return {
          label: t('dashboard.healthStatusUnknown'),
          className: 'health-badge-unknown',
          dotColor: 'var(--color-text-muted, #71717a)',
        };
    }
  };

  const overallBadge = health ? getStatusBadge(health.status) : null;

  const componentLabels: Record<string, { labelKey: TranslationKey; icon: string }> = {
    backend_api: {
      labelKey: 'dashboard.healthComponentBackend',
      icon: '⚡',
    },
    postgresql: {
      labelKey: 'dashboard.healthComponentDb',
      icon: '🗄️',
    },
    pgvector: {
      labelKey: 'dashboard.healthComponentVector',
      icon: '📐',
    },
    llm_service: {
      labelKey: 'dashboard.healthComponentLlm',
      icon: '🧠',
    },
    embedding_service: {
      labelKey: 'dashboard.healthComponentEmbedding',
      icon: '🔍',
    },
    reranker_service: {
      labelKey: 'dashboard.healthComponentReranker',
      icon: '🎯',
    },
  };

  const renderComponentItem = (key: string, item: DependencyHealth) => {
    const config = componentLabels[key] || {
      labelKey: 'dashboard.healthComponentBackend' as TranslationKey,
      icon: '⚙️',
    };
    const badge = getStatusBadge(item.status);

    return (
      <div
        key={key}
        className="health-component-item"
        data-testid={`health-component-${key}`}
      >
        <div className="health-component-header">
          <div className="health-component-name-group">
            <span className="health-component-icon">{config.icon}</span>
            <span className="health-component-title">
              {componentLabels[key] ? t(config.labelKey) : key}
            </span>
          </div>
          <span
            className={`health-badge ${badge.className}`}
            data-testid={`health-badge-${key}`}
          >
            <span
              className="health-badge-dot"
              style={{ backgroundColor: badge.dotColor }}
            />
            {badge.label}
          </span>
        </div>

        <div className="health-component-details">
          {item.details && (
            <span className="health-component-detail-text" data-testid={`health-detail-${key}`}>
              {item.details}
            </span>
          )}
          {item.latency_ms !== undefined && item.latency_ms !== null && (
            <span className="health-component-latency" data-testid={`health-latency-${key}`}>
              {item.latency_ms} ms
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="dashboard-panel health-monitoring-card" data-testid="system-health-card">
      {/* Header: Title + Overall Status + Manual Refresh */}
      <div className="panel-header">
        <div className="panel-header-title-group">
          <h3>{t('dashboard.healthTitle')}</h3>
          <p>{t('dashboard.healthDesc')}</p>
        </div>
        <div className="health-header-actions">
          {overallBadge && (
            <span
              className={`health-badge-pill ${overallBadge.className}`}
              data-testid="health-overall-status"
            >
              <span
                className="health-badge-dot"
                style={{ backgroundColor: overallBadge.dotColor }}
              />
              {overallBadge.label}
            </span>
          )}
          <button
            type="button"
            className="btn-health-refresh"
            onClick={onRefresh}
            disabled={isLoading}
            data-testid="btn-health-refresh"
            title="Làm mới trạng thái"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={isLoading ? 'spinning' : ''}
            >
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
          </button>
        </div>
      </div>

      {/* Components Grid */}
      {health && health.components ? (
        <div className="health-components-grid" data-testid="health-components-grid">
          {Object.entries(health.components).map(([key, item]) =>
            renderComponentItem(key, item)
          )}
        </div>
      ) : (
        <div className="health-empty-state" data-testid="health-empty-state">
          {isLoading ? t('dashboard.healthRefreshing') : t('dashboard.noActivity')}
        </div>
      )}

      {/* Footer info: Last Checked timestamp */}
      {health && health.timestamp && (
        <div className="health-card-footer" data-testid="health-last-checked">
          <span>{t('dashboard.healthLastChecked')}</span>
          <time dateTime={health.timestamp}>
            {new Date(health.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })}
          </time>
          {health.environment && (
            <span className="health-env-badge">env: {health.environment}</span>
          )}
        </div>
      )}
    </div>
  );
};