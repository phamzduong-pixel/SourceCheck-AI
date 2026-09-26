/**
 * AppLayout: Main Application Shell component integrating Sidebar, Header, and content outlet.
 */

import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useAIPreferences } from '../../hooks/useAIPreferences';
import '../../styles/layout.css';

export const AppLayout: React.FC = () => {
  const [isMobileOpen, setIsMobileOpen] = useState<boolean>(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const location = useLocation();
  const { t, activeChatTitle } = useAIPreferences();

  const getPageTitle = (pathname: string): string => {
    if (pathname === '/' || pathname.startsWith('/chat')) {
      return activeChatTitle || t('chat.title');
    }
    if (pathname.startsWith('/qa')) {
      return activeChatTitle || t('nav.qa');
    }
    if (pathname.startsWith('/fact-check')) return t('nav.factCheck');
    if (pathname.startsWith('/documents')) return t('nav.documents');
    if (pathname.startsWith('/search')) return t('nav.search');
    if (pathname.startsWith('/dashboard')) return t('nav.dashboard');
    if (pathname.startsWith('/settings')) return t('settings.title');
    if (pathname.startsWith('/profile')) return t('settings.profile');
    return 'SourceCheck AI';
  };

  const currentTitle = getPageTitle(location.pathname);

  return (
    <div
      className={`app-container ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}
      data-testid="app-layout"
    >
      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setIsMobileOpen(false)}
          data-testid="sidebar-backdrop"
        />
      )}

      {/* Persistent / Responsive Sidebar */}
      <Sidebar
        isOpen={isMobileOpen}
        onClose={() => setIsMobileOpen(false)}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
      />
      {!isMobileOpen && !isSidebarCollapsed && (
        <button
          type="button"
          className="sidebar-edge-collapse-toggle"
          onClick={() => setIsSidebarCollapsed(true)}
          aria-label="Thu gọn thanh bên"
          title="Thu gọn thanh bên"
          data-testid="sidebar-edge-collapse-toggle"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m15 6-6 6 6 6" />
          </svg>
        </button>
      )}

      {/* Main Workspace Area */}
      <div className="app-main">
        {/* Sticky Top Header */}
        <Header
          title={currentTitle}
          onToggleMobileMenu={() => setIsMobileOpen((prev) => !prev)}
        />

        {/* Scrollable Main Content */}
        <main className="app-content" data-testid="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
