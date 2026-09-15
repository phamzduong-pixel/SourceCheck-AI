/**
 * AILanguageSelector: Segmented control to choose AI Response Language (vi / en).
 * Supported by persistent state via useAIPreferences.
 */

import React from 'react';
import { useAIPreferences } from '../../hooks/useAIPreferences';

interface AILanguageSelectorProps {
  compact?: boolean;
}

export const AILanguageSelector: React.FC<AILanguageSelectorProps> = ({ compact = false }) => {
  const { aiLanguage, setAILanguage, t } = useAIPreferences();

  return (
    <div
      className={`ai-language-selector ${compact ? 'compact' : ''}`}
      data-testid="ai-language-selector"
      role="group"
      aria-label={t('ui.aiLanguageLabel')}
    >
      <span className="ai-lang-label" title={t('ui.aiLanguageLabel')}>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
        {!compact && <span>AI:</span>}
      </span>

      <div className="ai-lang-toggle-group">
        <button
          type="button"
          className={`ai-lang-btn ${aiLanguage === 'vi' ? 'active' : ''}`}
          onClick={() => setAILanguage('vi')}
          title="AI trả lời bằng Tiếng Việt"
          aria-pressed={aiLanguage === 'vi'}
          data-testid="ai-lang-btn-vi"
        >
          VI
        </button>
        <button
          type="button"
          className={`ai-lang-btn ${aiLanguage === 'en' ? 'active' : ''}`}
          onClick={() => setAILanguage('en')}
          title="AI responds in English"
          aria-pressed={aiLanguage === 'en'}
          data-testid="ai-lang-btn-en"
        >
          EN
        </button>
      </div>
    </div>
  );
};
