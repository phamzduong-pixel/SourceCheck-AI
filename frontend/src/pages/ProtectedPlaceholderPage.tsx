/**
 * ProtectedPlaceholderPage: Clean, minimalist protected entry point.
 * Confirms authenticated user state and allows sign out. (Chat UI is out-of-scope for Prompt 19B).
 */

import React from 'react';
import { useAuth } from '../hooks/useAuth';
import '../styles/auth.css';

export const ProtectedPlaceholderPage: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <div className="auth-container" style={{ justifyContent: 'flex-start', paddingTop: '4rem' }}>
      <div className="auth-card" style={{ maxWidth: '560px' }}>
        <div className="auth-header" style={{ marginBottom: '1.5rem' }}>
          <div className="auth-brand">
            <span>SourceCheck AI</span>
          </div>
          <h1 className="auth-title">Authenticated Workspace</h1>
          <p className="auth-subtitle">Phiên đăng nhập đang hoạt động an toàn</p>
        </div>

        <div
          style={{
            backgroundColor: '#f1f5f9',
            borderRadius: '10px',
            padding: '1.25rem',
            marginBottom: '1.5rem',
          }}
        >
          <div style={{ marginBottom: '0.75rem', fontSize: '0.9rem', color: '#475569' }}>
            <strong>Email:</strong> {user?.email}
          </div>
          <div style={{ marginBottom: '0.75rem', fontSize: '0.9rem', color: '#475569' }}>
            <strong>Họ tên:</strong> {user?.full_name || 'Chưa đặt tên'}
          </div>
          <div style={{ marginBottom: '0.75rem', fontSize: '0.9rem', color: '#475569' }}>
            <strong>Vai trò:</strong>{' '}
            <span
              style={{
                backgroundColor: '#e2e8f0',
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                fontSize: '0.8rem',
                fontWeight: 600,
                textTransform: 'uppercase',
              }}
            >
              {user?.role || 'user'}
            </span>
          </div>
          <div style={{ fontSize: '0.85rem', color: '#16a34a', fontWeight: 500 }}>
            ● Trạng thái: Đã xác thực thành công (Ready)
          </div>
        </div>

        <div style={{ textAlign: 'center' }}>
          <button
            type="button"
            className="auth-btn-primary"
            onClick={logout}
            style={{
              backgroundColor: '#ffffff',
              color: '#dc2626',
              border: '1px solid #fca5a5',
            }}
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
};
