/**
 * UILanguageSelector: Segmented control to choose System UI Language (vi / en).
 * Supported by persistent state via useAIPreferences.
 */

import React from 'react';
import { useAIPreferences } from '../../hooks/useAIPreferences';

interface UILanguageSelectorProps {
  compact?: boolean;
}

export const UILanguageSelector: React.FC<UILanguageSelectorProps> = ({ compact = false }) => {
  const { uiLanguage, setUILanguage, t } = useAIPreferences();

  return (
    <div
      className={`lang-selector ui-language-selector ${compact ? 'compact' : ''}`}
      data-testid="ui-language-selector"
      role="group"
      aria-label={t('ui.uiLanguageLabel')}
    >
      <span className="ai-lang-label" title={t('ui.uiLanguageLabel')}>
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
          <path d="m5 8 6 6" />
          <path d="m4 14 6-6 2-3" />
          <path d="M2 5h12" />
          <path d="M7 2h1" />
          <path d="m22 22-5-10-5 10" />
          <path d="M14 18h6" />
        </svg>
        {!compact && <span>UI:</span>}
      </span>

      <div className="lang-toggle-group">
        <button
          type="button"
          className={`lang-btn ${uiLanguage === 'vi' ? 'active' : ''}`}
          onClick={() => setUILanguage('vi')}
          title="Giao diện Tiếng Việt"
          aria-pressed={uiLanguage === 'vi'}
          data-testid="ui-lang-btn-vi"
        >
          VI
        </button>
        <button
          type="button"
          className={`lang-btn ${uiLanguage === 'en' ? 'active' : ''}`}
          onClick={() => setUILanguage('en')}
          title="English"
          aria-pressed={uiLanguage === 'en'}
          data-testid="ui-lang-btn-en"
        >
          EN
        </button>
      </div>
    </div>
  );
};
