import React from 'react';
import { SystemStatusIndicator } from './SystemStatusIndicator';
import { ThemeToggle } from './ThemeToggle';
import { useAIPreferences } from '../../hooks/useAIPreferences';

interface HeaderProps {
  onToggleMobileMenu?: () => void;
  title?: string;
}

export const Header: React.FC<HeaderProps> = ({
  onToggleMobileMenu,
  title,
}) => {
  const { t } = useAIPreferences();
  const displayTitle = title || t('dashboard.heroBadge');

  return (
    <header className="app-header" data-testid="app-header">
      {/* Left: Mobile Toggle & Page Title */}
      <div className="header-left">
        <button
          type="button"
          className="mobile-menu-toggle"
          onClick={onToggleMobileMenu}
          aria-label="Toggle navigation menu"
          data-testid="mobile-menu-toggle"
        >
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="4" x2="20" y1="12" y2="12" />
            <line x1="4" x2="20" y1="6" y2="6" />
            <line x1="4" x2="20" y1="18" y2="18" />
          </svg>
        </button>
        <h2 className="header-title">{displayTitle}</h2>
      </div>

      {/* Right: Theme Toggle & System Status Badge */}
      <div className="header-right">
        <ThemeToggle />
        <SystemStatusIndicator />
      </div>
    </header>
  );
};
