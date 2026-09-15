import React from 'react';
import { DashboardStats } from '../../types/dashboard';
import { TranslationKey } from '../../i18n/types';

interface DashboardSummaryCardsProps {
  stats: DashboardStats;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

export const DashboardSummaryCards: React.FC<DashboardSummaryCardsProps> = ({ stats, t }) => {
  const totalDocs = Number(stats?.total_documents ?? 0);
  const totalChunks = Number(stats?.total_chunks ?? 0);
  const totalQuestions = Number(stats?.total_questions ?? 0);
  const totalConversations = Number(stats?.total_conversations ?? 0);
  const totalVerifications = Number(stats?.total_verifications ?? 0);
  const totalClaims = Number(stats?.total_claims_verified ?? 0);

  return (
    <div className="summary-cards-grid" data-testid="dashboard-summary-cards">
      {/* 1. Documents */}
      <div className="summary-card" data-testid="stat-documents">
        <div className="summary-card-header">
          <span className="summary-card-label">{t('dashboard.totalDocuments')}</span>
          <div className="summary-card-icon docs">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
              <path d="M6 6h10" />
              <path d="M6 10h10" />
            </svg>
          </div>
        </div>
        <div className="summary-card-value" data-testid="stat-documents-value">
          {totalDocs.toLocaleString()}
        </div>
      </div>

      {/* 2. Chunks */}
      <div className="summary-card" data-testid="stat-chunks">
        <div className="summary-card-header">
          <span className="summary-card-label">{t('dashboard.totalChunks')}</span>
          <div className="summary-card-icon chunks">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect width="7" height="7" x="3" y="3" rx="1" />
              <rect width="7" height="7" x="14" y="3" rx="1" />
              <rect width="7" height="7" x="14" y="14" rx="1" />
              <rect width="7" height="7" x="3" y="14" rx="1" />
            </svg>
          </div>
        </div>
        <div className="summary-card-value" data-testid="stat-chunks-value">
          {totalChunks.toLocaleString()}
        </div>
      </div>

      {/* 3. Questions */}
      <div className="summary-card" data-testid="stat-questions">
        <div className="summary-card-header">
          <span className="summary-card-label">{t('dashboard.totalQuestions')}</span>
          <div className="summary-card-icon questions">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
              <path d="M12 17h.01" />
            </svg>
          </div>
        </div>
        <div className="summary-card-value" data-testid="stat-questions-value">
          {totalQuestions.toLocaleString()}
        </div>
      </div>

      {/* 4. Conversations */}
      <div className="summary-card" data-testid="stat-conversations">
        <div className="summary-card-header">
          <span className="summary-card-label">{t('dashboard.totalConversations')}</span>
          <div className="summary-card-icon conversations">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
        </div>
        <div className="summary-card-value" data-testid="stat-conversations-value">
          {totalConversations.toLocaleString()}
        </div>
      </div>

      {/* 5. Verifications */}
      <div className="summary-card" data-testid="stat-verifications">
        <div className="summary-card-header">
          <span className="summary-card-label">{t('dashboard.totalVerifications')}</span>
          <div className="summary-card-icon verifications">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </div>
        </div>
        <div className="summary-card-value" data-testid="stat-verifications-value">
          {totalVerifications.toLocaleString()}
        </div>
      </div>

      {/* 6. Claims */}
      <div className="summary-card" data-testid="stat-claims">
        <div className="summary-card-header">
          <span className="summary-card-label">{t('dashboard.totalClaims')}</span>
          <div className="summary-card-icon claims">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <polyline points="16 11 18 13 22 9" />
            </svg>
          </div>
        </div>
        <div className="summary-card-value" data-testid="stat-claims-value">
          {totalClaims.toLocaleString()}
        </div>
      </div>
    </div>
  );
};
