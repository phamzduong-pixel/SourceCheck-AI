import React, { useState, useRef, useEffect } from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useAIPreferences } from '../../hooks/useAIPreferences';
import ConversationList from './ConversationList';
import { UILanguageSelector } from './UILanguageSelector';
import { AILanguageSelector } from './AILanguageSelector';
import { ThemeToggle } from './ThemeToggle';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen = false,
  onClose,
  isCollapsed = false,
  onToggleCollapse,
}) => {
  const { user, logout } = useAuth();
  const { t } = useAIPreferences();
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const handleNavClick = () => {
    if (onClose) {
      onClose();
    }
  };

  const handleNewChat = () => {
    handleNavClick();
    window.dispatchEvent(new CustomEvent('sourcecheck:new-chat'));
    navigate('/', { state: { newChatAt: Date.now() } });
  };

  const handleLogout = () => {
    setIsMenuOpen(false);
    if (onClose) {
      onClose();
    }
    logout();
  };

  // Close menu on click outside or Escape key
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsMenuOpen(false);
      }
    };

    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isMenuOpen]);

  const displayName = user?.full_name || user?.email?.split('@')[0] || t('user.demoUser');
  const roleName = user?.role || 'User';
  const initials = displayName
    .split(' ')
    .filter(Boolean)
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase() || 'U';

  return (
    <aside
      className={`app-sidebar ${isOpen ? 'open' : ''} ${isCollapsed ? 'collapsed' : ''}`}
      data-testid="app-sidebar"
    >
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <button
            type="button"
            className="sidebar-brand-toggle"
            onClick={onToggleCollapse}
            aria-label={isCollapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
            aria-pressed={isCollapsed}
            title={isCollapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
            data-testid="sidebar-brand-toggle"
          >
            <svg
              className="nav-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </button>
          <Link to="/" className="sidebar-brand-link" onClick={handleNavClick}>
            <span>{t('brand.name')}</span>
            <span className="sidebar-brand-badge">AI</span>
          </Link>
        </div>
      </div>

      {/* Prominent '+ Tra cứu mới' Action */}
      <div className="sidebar-new-chat-container">
        <button
          type="button"
          className="btn-sidebar-new-chat"
          onClick={handleNewChat}
          data-testid="sidebar-new-chat-btn"
          aria-label={t('nav.newChat')}
          title={t('nav.newChat')}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>{t('chat.newChatBtn')}</span>
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav">
        {/* Research History */}
        <ConversationList />

        {/* Specialized Tools Group */}
        <div className="nav-section-title">{t('nav.tools')}</div>

        <NavLink
          to="/dashboard"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          onClick={handleNavClick}
          title={t('nav.dashboard')}
        >
          <svg
            className="nav-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect width="7" height="9" x="3" y="3" rx="1" />
            <rect width="7" height="5" x="14" y="3" rx="1" />
            <rect width="7" height="9" x="14" y="12" rx="1" />
            <rect width="7" height="5" x="3" y="16" rx="1" />
          </svg>
          <span>{t('nav.dashboard')}</span>
        </NavLink>

        <NavLink
          to="/verification-history"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          onClick={handleNavClick}
          title="Lịch sử kiểm chứng"
        >
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 12a9 9 0 1 0 3-6.7" />
            <path d="M3 4v5h5" />
            <path d="M12 7v5l3 2" />
          </svg>
          <span>Lịch sử kiểm chứng</span>
        </NavLink>
        <NavLink
          to="/fact-check"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          onClick={handleNavClick}
          title={t('nav.factCheck')}
        >
          <svg
            className="nav-icon"
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
          <span>{t('nav.factCheck')}</span>
        </NavLink>

        <NavLink
          to="/documents"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          onClick={handleNavClick}
          title={t('nav.documents')}
        >
          <svg
            className="nav-icon"
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
          <span>{t('nav.documents')}</span>
        </NavLink>

        <NavLink
          to="/search"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          onClick={handleNavClick}
          title={t('nav.search')}
        >
          <svg
            className="nav-icon"
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
          <span>{t('nav.search')}</span>
        </NavLink>
      </nav>

      {/* User Profile in Sidebar Bottom (DeepSeek / AI Assistant Style) */}
      <div className="sidebar-user-section" data-testid="sidebar-user-section" ref={userMenuRef}>
        {/* Dropdown Popup Menu */}
        {isMenuOpen && (
          <div className="user-account-menu" data-testid="user-account-menu" role="menu">
            <div className="menu-section-label">{t('settings.profile')}</div>
            <div className="menu-header">
              <div className="menu-user-avatar" aria-hidden="true">
                {user?.avatar_url ? <img src={user.avatar_url} alt="" className="sidebar-avatar-image" /> : initials}
              </div>
              <div className="menu-user-info">
                <span className="menu-user-name" data-testid="dropdown-user-name">
                  {displayName}
                </span>
                <span className="menu-user-email" data-testid="dropdown-user-email">
                  {user?.email || 'demo@sourcecheck.ai'}
                </span>
                <span className="menu-user-role" data-testid="dropdown-user-role">
                  {roleName}
                </span>
              </div>
            </div>

            <div className="menu-divider" />
            <button
              type="button"
              className="menu-profile-btn"
              onClick={() => {
                setIsMenuOpen(false);
                navigate('/profile');
              }}
              data-testid="profile-open-btn"
              role="menuitem"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="8" r="3" />
                <path d="M5 20a7 7 0 0 1 14 0" />
              </svg>
              <span>{t('settings.profileAction')}</span>
            </button>
            <div className="menu-divider" />

            {/* Language & Theme Preferences inside User Menu */}
            <div className="menu-section-label">{t('settings.title')}</div>
            <div className="menu-section">
              <div className="menu-preference-item">
                <span className="menu-pref-title">{t('user.uiLanguage')}</span>
                <UILanguageSelector />
              </div>
              <div className="menu-preference-item">
                <span className="menu-pref-title">{t('user.aiResponseLanguage')}</span>
                <AILanguageSelector />
              </div>
              <div className="menu-preference-item">
                <span className="menu-pref-title">{t('user.theme')}</span>
                <ThemeToggle />
              </div>
            </div>

            <button
              type="button"
              className="menu-settings-btn"
              onClick={() => {
                setIsMenuOpen(false);
                navigate('/settings');
              }}
              data-testid="profile-settings-btn"
              role="menuitem"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-1.7 1.7-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V20h-2.4v-.2a1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-1.7-1.7.06-.06A1.7 1.7 0 0 0 8.4 15a1.7 1.7 0 0 0-1.56-1.03H6v-2.4h.84A1.7 1.7 0 0 0 8.4 10a1.7 1.7 0 0 0-.34-1.88L8 8.06l1.7-1.7.06.06A1.7 1.7 0 0 0 11.64 6.1 1.7 1.7 0 0 0 12.67 4.5V4h2.4v.5A1.7 1.7 0 0 0 16.1 6.1a1.7 1.7 0 0 0 1.88-.34l.06-.06 1.7 1.7-.06.06A1.7 1.7 0 0 0 19.4 10a1.7 1.7 0 0 0 1.56 1.03h.04v2.4h-.04A1.7 1.7 0 0 0 19.4 15Z" />
              </svg>
              <span>{t('settings.title')}</span>
            </button>

            <div className="menu-divider" />

            {/* Sign Out Button */}
            <button
              type="button"
              className="menu-signout-btn"
              onClick={handleLogout}
              data-testid="btn-signout"
              role="menuitem"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" x2="9" y1="12" y2="12" />
              </svg>
              <span>{t('user.signOut')}</span>
            </button>
          </div>
        )}

        {/* User Card Trigger */}
        <div className="user-menu-wrapper" data-testid="user-menu-wrapper">
          <button
            type="button"
            className={`sidebar-user-card ${isMenuOpen ? 'active' : ''}`}
            onClick={() => setIsMenuOpen((prev) => !prev)}
            data-testid="user-menu-trigger"
            aria-expanded={isMenuOpen}
            aria-haspopup="true"
            title={t('user.accountSettings')}
          >
            <div className="sidebar-user-avatar" aria-hidden="true">
              {user?.avatar_url ? <img src={user.avatar_url} alt="" className="sidebar-avatar-image" /> : initials}
            </div>

            <div className="sidebar-user-details">
              <span className="sidebar-user-name" title={displayName} data-testid="sidebar-user-name">
                {displayName}
              </span>
              <span className="sidebar-user-role">{roleName}</span>
            </div>

            <div className="sidebar-user-chevron" aria-hidden="true">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ transform: isMenuOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}
              >
                <polyline points="18 15 12 9 6 15" />
              </svg>
            </div>
          </button>
        </div>

        <div className="sidebar-version-footer">
          <span>{t('nav.version')}</span>
          <span>v0.1.0</span>
        </div>
      </div>
    </aside>
  );
};