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
  const location = useLocation();
  const { t } = useAIPreferences();

  const getPageTitle = (pathname: string): string => {
    if (pathname === '/' || pathname.startsWith('/chat')) return t('chat.title');
    if (pathname.startsWith('/qa')) return t('nav.qa');
    if (pathname.startsWith('/fact-check')) return t('nav.factCheck');
    if (pathname.startsWith('/documents')) return t('nav.documents');
    if (pathname.startsWith('/search')) return t('nav.search');
    if (pathname.startsWith('/dashboard')) return t('nav.dashboard');
    return 'SourceCheck AI';
  };

  const currentTitle = getPageTitle(location.pathname);

  return (
    <div className="app-container" data-testid="app-layout">
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
      />

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
