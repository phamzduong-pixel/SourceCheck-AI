// src/components/layout/ConversationList.tsx
import React, { useEffect, useState, useRef } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import conversationService, { Conversation } from '../../services/conversations';
import { useAIPreferences } from '../../hooks/useAIPreferences';
import { DeleteConversationModal } from './DeleteConversationModal';

const ConversationList: React.FC = () => {
  const { t } = useAIPreferences();
  const location = useLocation();
  const navigate = useNavigate();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Context Menu & Delete Modal state
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const [deletingConvId, setDeletingConvId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const menuRef = useRef<HTMLDivElement>(null);

  const fetchConversations = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await conversationService.listConversations();
      setConversations(Array.isArray(data) ? data : []);
    } catch (err: any) {
      // If 401 unauthorized, user has no active session yet - gracefully treat as empty list rather than raw error
      if (err?.statusCode === 401 || err?.message?.includes('Bearer token required') || err?.message?.includes('xác thực')) {
        setConversations([]);
        setError(null);
      } else {
        setError(err?.message || t('common.error'));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();

    const onRefresh = () => {
      fetchConversations();
    };
    window.addEventListener('sourcecheck:refresh-conversations', onRefresh);
    return () => {
      window.removeEventListener('sourcecheck:refresh-conversations', onRefresh);
    };
  }, []);

  // Click outside listener for context menu
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setActiveMenuId(null);
      }
    };
    if (activeMenuId) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [activeMenuId]);

  const safeConversations = Array.isArray(conversations) ? conversations : [];
  const sorted = [...safeConversations].sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) {
      return a.is_pinned ? -1 : 1;
    }
    const timeA = new Date(a.updated_at || a.created_at || 0).getTime();
    const timeB = new Date(b.updated_at || b.created_at || 0).getTime();
    if (timeA !== timeB) {
      return timeB - timeA;
    }
    return a.id < b.id ? 1 : -1;
  });

  const handleTogglePin = async (c: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setActiveMenuId(null);
    try {
      const updated = await conversationService.updateConversation(c.id, {
        is_pinned: !c.is_pinned,
      });
      setConversations((prev) =>
        prev.map((item) => (item.id === c.id ? { ...item, is_pinned: updated.is_pinned } : item))
      );
    } catch (err: any) {
      setDeleteError(err?.message || t('common.error'));
    }
  };

  const handleRename = async (c: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setActiveMenuId(null);
    const newTitle = window.prompt(t('chat.rename'), c.title);
    if (newTitle && newTitle.trim() && newTitle.trim() !== c.title) {
      try {
        const updated = await conversationService.updateConversation(c.id, {
          title: newTitle.trim(),
        });
        setConversations((prev) =>
          prev.map((item) => (item.id === c.id ? { ...item, title: updated.title } : item))
        );
      } catch (err: any) {
        setDeleteError(err?.message || t('common.error'));
      }
    }
  };

  const handleOpenDeleteModal = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setActiveMenuId(null);
    setDeleteError(null);
    setDeletingConvId(id);
  };

  const handleConfirmDelete = async () => {
    if (!deletingConvId) return;

    setIsDeleting(true);
    setDeleteError(null);

    const idToDelete = deletingConvId;
    const isCurrentlyActive = location.pathname.includes(`/chat/${idToDelete}`);

    try {
      await conversationService.deleteConversation(idToDelete);

      // On Success: Update state immediately
      setConversations((prev) => prev.filter((item) => item.id !== idToDelete));
      setDeletingConvId(null);

      // If active conversation was deleted -> Clear messages and redirect to welcome empty state
      if (isCurrentlyActive) {
        window.dispatchEvent(new CustomEvent('sourcecheck:new-chat'));
        navigate('/', { replace: true });
      }
    } catch (err: any) {
      // On Failure: Do NOT delete item from UI, show error alert and allow retry
      setDeleteError(err?.message || t('chat.deleteError'));
    } finally {
      setIsDeleting(false);
    }
  };

  let content;
  if (loading) {
    content = (
      <div className="sidebar-history-loading" data-testid="sidebar-history-loading">
        <div className="loading-spinner" role="status" aria-label={t('common.loading')}></div>
      </div>
    );
  } else if (error) {
    content = (
      <div className="sidebar-history-error" data-testid="sidebar-history-error">
        <div>{error}</div>
        <button type="button" className="btn-retry" onClick={fetchConversations}>
          ↻
        </button>
      </div>
    );
  } else if (sorted.length === 0) {
    content = (
      <div className="sidebar-history-empty" data-testid="sidebar-history-empty">
        <span>{t('chat.noHistory')}</span>
      </div>
    );
  } else {
    content = (
      <div className="sidebar-history-list" data-testid="sidebar-history-list">
        {deleteError && (
          <div className="delete-error-alert" data-testid="delete-error-alert" role="alert">
            <span>{deleteError}</span>
            <button
              type="button"
              className="btn-close-error"
              onClick={() => setDeleteError(null)}
              aria-label={t('common.close')}
            >
              ✕
            </button>
          </div>
        )}

        {sorted.map((c) => {
          const isMenuOpen = activeMenuId === c.id;
          return (
            <div key={c.id} className="history-item-wrapper" ref={isMenuOpen ? menuRef : null}>
              <NavLink
                to={`/chat/${c.id}`}
                className={({ isActive }) => `nav-item history-item ${isActive ? 'active' : ''}`}
                data-testid={`history-item-${c.id}`}
              >
                <div className="history-item-content">
                  {c.is_pinned && (
                    <span className="pinned-badge" title={t('chat.pin')} aria-label={t('chat.pin')}>
                      📌
                    </span>
                  )}
                  <span className="history-item-title">{c.title || t('chat.newChatBtn')}</span>
                </div>

                <button
                  type="button"
                  className={`btn-conversation-menu ${isMenuOpen ? 'active' : ''}`}
                  data-testid={`conversation-menu-trigger-${c.id}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    setActiveMenuId(isMenuOpen ? null : c.id);
                  }}
                  aria-label={t('common.actions')}
                  aria-expanded={isMenuOpen}
                >
                  •••
                </button>
              </NavLink>

              {/* Context Action Menu Dropdown */}
              {isMenuOpen && (
                <div
                  className="conversation-action-menu"
                  data-testid={`conversation-action-menu-${c.id}`}
                  role="menu"
                >
                  <button
                    type="button"
                    className="menu-action-item"
                    data-testid={`action-rename-${c.id}`}
                    onClick={(e) => handleRename(c, e)}
                    role="menuitem"
                  >
                    <svg className="menu-action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
                    <span>{t('chat.rename')}</span>
                  </button>

                  <button
                    type="button"
                    className="menu-action-item"
                    data-testid={`action-pin-${c.id}`}
                    onClick={(e) => handleTogglePin(c, e)}
                    role="menuitem"
                  >
                    <svg className="menu-action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m12 17 5-5V5l1-1H6l1 1v7Z"/><path d="M12 17v5"/><path d="M8 4h8"/></svg>
                    <span>{c.is_pinned ? t('chat.unpin') : t('chat.pin')}</span>
                  </button>

                  <div className="menu-action-divider" />

                  <button
                    type="button"
                    className="menu-action-item danger"
                    data-testid={`action-delete-${c.id}`}
                    onClick={(e) => handleOpenDeleteModal(c.id, e)}
                    role="menuitem"
                  >
                    <svg className="menu-action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v5"/><path d="M14 11v5"/></svg>
                    <span>{t('chat.delete')}</span>
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="sidebar-history-section" data-testid="sidebar-history-section">
      {content}

      <DeleteConversationModal
        isOpen={deletingConvId !== null}
        isDeleting={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          if (!isDeleting) {
            setDeletingConvId(null);
            setDeleteError(null);
          }
        }}
      />
    </div>
  );
};

export default ConversationList;
