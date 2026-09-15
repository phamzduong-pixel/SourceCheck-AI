import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
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
  const { t, activeChatTitle } = useAIPreferences();
  const location = useLocation();
  const navigate = useNavigate();

  const isChatRoute =
    location.pathname === '/' ||
    location.pathname.startsWith('/chat') ||
    location.pathname.startsWith('/qa');

  const displayTitle =
    isChatRoute && activeChatTitle
      ? activeChatTitle
      : title || t('dashboard.heroBadge');

  const handleNewChat = () => {
    window.dispatchEvent(new CustomEvent('sourcecheck:new-chat'));
    if (location.pathname.startsWith('/chat/')) {
      navigate('/', { replace: true });
    }
  };

  return (
    <header className="app-header" data-testid="app-header">
      {/* Left: Mobile Toggle & Page / Conversation Title */}
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

        <div className="header-title-wrapper" title={displayTitle}>
          <h2 className="header-title">{displayTitle}</h2>
          {isChatRoute && activeChatTitle && (
            <span className="header-chat-badge" title="Cuộc trò chuyện đã được đối soát trích dẫn">
              ● Grounded
            </span>
          )}
        </div>
      </div>

      {/* Right: + Tra cứu mới button, Theme Toggle & System Status Badge */}
      <div className="header-right">
        {isChatRoute && activeChatTitle && (
          <button
            type="button"
            className="header-btn-new-chat"
            onClick={handleNewChat}
            title={t('chat.resetTooltip')}
            data-testid="header-btn-new-chat"
            aria-label="Tra cứu mới"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span>{t('chat.newChatBtn')}</span>
          </button>
        )}
        <ThemeToggle />
        <SystemStatusIndicator />
      </div>
    </header>
  );
};

