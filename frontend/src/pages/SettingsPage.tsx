import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAIPreferences } from '../hooks/useAIPreferences';
import { UILanguageSelector } from '../components/layout/UILanguageSelector';
import { AILanguageSelector } from '../components/layout/AILanguageSelector';
import '../styles/settings.css';

export const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    t,
    theme,
    setTheme,
    showSources,
    setShowSources,
    showVerification,
    setShowVerification,
    fontSize,
    setFontSize,
  } = useAIPreferences();

  return (
    <div className="settings-page" data-testid="settings-page">
      <div className="settings-header">
        <button
          type="button"
          className="settings-back-button"
          onClick={() => navigate(-1)}
          data-testid="settings-back"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m15 18-6-6 6-6" />
          </svg>
          <span>{t('settings.back')}</span>
        </button>
        <div>
          <h1>{t('settings.title')}</h1>
          <p>{t('settings.subtitle')}</p>
        </div>
      </div>

      <div className="settings-sections">
        <section className="settings-section" aria-labelledby="settings-appearance-title">
          <div className="settings-section-heading">
            <h2 id="settings-appearance-title">{t('settings.appearance')}</h2>
          </div>
          <div className="settings-row settings-row-theme">
            <div className="settings-row-copy">
              <h3>{t('settings.theme')}</h3>
              <p>{t('settings.themeDescription')}</p>
            </div>
            <div className="settings-segmented" role="group" aria-label={t('settings.theme')}>
              <button
                type="button"
                className={theme === 'light' ? 'active' : ''}
                aria-pressed={theme === 'light'}
                data-testid="settings-theme-light"
                onClick={() => setTheme('light')}
              >
                {t('settings.light')}
              </button>
              <button
                type="button"
                className={theme === 'dark' ? 'active' : ''}
                aria-pressed={theme === 'dark'}
                data-testid="settings-theme-dark"
                onClick={() => setTheme('dark')}
              >
                {t('settings.dark')}
              </button>
            </div>
          </div>
        </section>

        <section className="settings-section" aria-labelledby="settings-font-size-title">
          <div className="settings-section-heading">
            <h2 id="settings-font-size-title">{t('settings.appearance')}</h2>
          </div>
          <div className="settings-row settings-row-theme">
            <div className="settings-row-copy">
              <h3>{t('settings.fontSize')}</h3>
              <p>{t('settings.fontSizeDescription')}</p>
            </div>
            <div className="settings-segmented settings-font-size" role="group" aria-label={t('settings.fontSize')}>
              {(['small', 'medium', 'large'] as const).map((size) => (
                <button
                  type="button"
                  key={size}
                  className={fontSize === size ? 'active' : ''}
                  aria-pressed={fontSize === size}
                  data-testid={`settings-font-size-${size}`}
                  onClick={() => setFontSize(size)}
                >
                  {t(size === 'small' ? 'settings.fontSmall' : size === 'large' ? 'settings.fontLarge' : 'settings.fontMedium')}
                </button>
              ))}
            </div>
          </div>
        </section>
        <section className="settings-section" aria-labelledby="settings-language-title">
          <div className="settings-section-heading">
            <h2 id="settings-language-title">{t('settings.language')}</h2>
          </div>
          <div className="settings-row">
            <div className="settings-row-copy">
              <h3>{t('settings.uiLanguage')}</h3>
            </div>
            <UILanguageSelector />
          </div>
          <div className="settings-row">
            <div className="settings-row-copy">
              <h3>{t('settings.aiLanguage')}</h3>
            </div>
            <AILanguageSelector />
          </div>
        </section>

        <section className="settings-section" aria-labelledby="settings-experience-title">
          <div className="settings-section-heading">
            <h2 id="settings-experience-title">{t('settings.experience')}</h2>
          </div>
          <div className="settings-row">
            <div className="settings-row-copy">
              <h3>{t('settings.showSources')}</h3>
              <p>{t('settings.showSourcesDescription')}</p>
            </div>
            <button
              type="button"
              className={`settings-switch ${showSources ? 'active' : ''}`}
              role="switch"
              aria-checked={showSources}
              data-testid="settings-show-sources"
              onClick={() => setShowSources(!showSources)}
            >
              <span aria-hidden="true" />
            </button>
          </div>
          <div className="settings-row">
            <div className="settings-row-copy">
              <h3>{t('settings.showVerification')}</h3>
              <p>{t('settings.showVerificationDescription')}</p>
            </div>
            <button
              type="button"
              className={`settings-switch ${showVerification ? 'active' : ''}`}
              role="switch"
              aria-checked={showVerification}
              data-testid="settings-show-verification"
              onClick={() => setShowVerification(!showVerification)}
            >
              <span aria-hidden="true" />
            </button>
          </div>
        </section>

        <section className="settings-section" aria-labelledby="settings-data-title">
          <div className="settings-section-heading">
            <h2 id="settings-data-title">{t('settings.data')}</h2>
          </div>
          <div className="settings-row settings-row-info">
            <div className="settings-row-copy">
              <h3>{t('settings.localHistory')}</h3>
              <p>{t('settings.localHistoryDescription')}</p>
            </div>
            <span className="settings-info-badge">{t('settings.localHistoryUnavailable')}</span>
          </div>
        </section>
      </div>
    </div>
  );
};