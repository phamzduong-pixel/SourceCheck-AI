import React from 'react';
import { Link } from 'react-router-dom';
import { TranslationKey } from '../../i18n/types';

interface QuickActionsGridProps {
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

export const QuickActionsGrid: React.FC<QuickActionsGridProps> = ({ t }) => {
  return (
    <div className="feature-grid" data-testid="dashboard-quick-actions">
      {/* Card 1: Grounded Q&A */}
      <Link to="/qa" className="feature-card" data-testid="card-qa">
        <div className="feature-card-icon-wrapper qa">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            <path d="M12 7v3" />
            <path d="M12 13h.01" />
          </svg>
        </div>
        <h3>{t('dashboard.cardQaTitle')}</h3>
        <p>{t('dashboard.cardQaDesc')}</p>
        <div className="feature-card-action">
          <span>{t('dashboard.cardQaAction')}</span>
          <span>&rarr;</span>
        </div>
      </Link>

      {/* Card 2: Fact-Checking Verification */}
      <Link to="/fact-check" className="feature-card" data-testid="card-fact-check">
        <div className="feature-card-icon-wrapper verify">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        </div>
        <h3>{t('dashboard.cardFactCheckTitle')}</h3>
        <p>{t('dashboard.cardFactCheckDesc')}</p>
        <div className="feature-card-action">
          <span>{t('dashboard.cardFactCheckAction')}</span>
          <span>&rarr;</span>
        </div>
      </Link>

      {/* Card 3: Document Management */}
      <Link to="/documents" className="feature-card" data-testid="card-documents">
        <div className="feature-card-icon-wrapper doc">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
            <path d="M6 6h10" />
            <path d="M6 10h10" />
          </svg>
        </div>
        <h3>{t('dashboard.cardDocTitle')}</h3>
        <p>{t('dashboard.cardDocDesc')}</p>
        <div className="feature-card-action">
          <span>{t('dashboard.cardDocAction')}</span>
          <span>&rarr;</span>
        </div>
      </Link>

      {/* Card 4: Search Explorer */}
      <Link to="/search" className="feature-card" data-testid="card-search">
        <div className="feature-card-icon-wrapper search">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
        </div>
        <h3>{t('dashboard.cardSearchTitle')}</h3>
        <p>{t('dashboard.cardSearchDesc')}</p>
        <div className="feature-card-action">
          <span>{t('dashboard.cardSearchAction')}</span>
          <span>&rarr;</span>
        </div>
      </Link>
    </div>
  );
};
