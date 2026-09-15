import React from 'react';
import { RecentActivityItem } from '../../types/dashboard';
import { TranslationKey } from '../../i18n/types';

interface RecentActivityFeedProps {
  activities: RecentActivityItem[];
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

export const RecentActivityFeed: React.FC<RecentActivityFeedProps> = ({ activities, t }) => {
  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const renderTypeIcon = (type: string) => {
    switch (type) {
      case 'document':
        return (
          <div className="activity-type-icon document" title="Document">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
              <path d="M6 6h10" />
            </svg>
          </div>
        );
      case 'question':
        return (
          <div className="activity-type-icon question" title="Grounded Question">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
              <path d="M12 17h.01" />
            </svg>
          </div>
        );
      case 'verification':
        return (
          <div className="activity-type-icon verification" title="Verification">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </div>
        );
      case 'conversation':
      default:
        return (
          <div className="activity-type-icon conversation" title="Conversation">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
        );
    }
  };

  const getStatusClass = (status?: string) => {
    if (!status) return 'neutral';
    const s = status.toLowerCase();
    if (s.includes('support') || s === 'true' || s === 'ingested' || s === 'completed') return 'supported';
    if (s.includes('refut') || s === 'false') return 'refuted';
    if (s.includes('part') || s === 'mixed') return 'mixed';
    return 'neutral';
  };

  return (
    <div className="dashboard-panel-card" data-testid="recent-activity-card">
      <div className="panel-card-header">
        <div>
          <h2>{t('dashboard.recentActivityTitle')}</h2>
          <p>{t('dashboard.recentActivityDesc')}</p>
        </div>
      </div>

      {activities.length === 0 ? (
        <div className="dashboard-empty-state" data-testid="recent-activity-empty">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{t('dashboard.noActivity')}</span>
        </div>
      ) : (
        <div className="activity-feed-list" data-testid="activity-feed-list">
          {activities.map((item) => (
            <div key={item.id} className="activity-item" data-testid={`activity-item-${item.id}`}>
              {renderTypeIcon(item.type)}
              <div className="activity-details">
                <div className="activity-title" title={item.title}>
                  {item.title}
                </div>
                {item.description && item.description !== item.title && (
                  <div className="activity-desc" title={item.description}>
                    {item.description}
                  </div>
                )}
                <div className="activity-footer">
                  <span className="activity-time">{formatTime(item.created_at)}</span>
                  {item.status && (
                    <span className={`activity-status-badge ${getStatusClass(item.status)}`}>
                      {item.status}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
