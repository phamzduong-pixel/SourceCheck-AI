/**
 * OAuthCallbackPage: Handles OAuth redirect callbacks (Google OAuth).
 * Exchanges authorization code for JWT token and redirects user to protected route.
 */

import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import '../styles/auth.css';

export const OAuthCallbackPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithGoogle, loginWithToken } = useAuth();

  const [statusText, setStatusText] = useState('Đang xác thực tài khoản Google...');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Prevent multiple executions in React StrictMode
  const hasExecutedRef = useRef(false);

  useEffect(() => {
    if (hasExecutedRef.current) return;
    hasExecutedRef.current = true;

    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const token = searchParams.get('token');
    const errorParam = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');

    // 1. Check if OAuth provider returned an error (e.g. user cancelled)
    if (errorParam) {
      if (errorParam === 'access_denied') {
        setErrorMessage('Bạn đã hủy quá trình đăng nhập bằng Google.');
      } else {
        setErrorMessage(
          errorDescription || `Đăng nhập Google thất bại: ${errorParam}`
        );
      }
      return;
    }

    // 2. Direct token passing (e.g., if backend redirected with ?token=...)
    if (token) {
      setStatusText('Đang hoàn tất đăng nhập...');
      loginWithToken(token)
        .then(() => {
          navigate('/', { replace: true });
        })
        .catch((err: any) => {
          setErrorMessage(
            err?.message || 'Không thể xác thực token. Vui lòng đăng nhập lại.'
          );
        });
      return;
    }

    // 3. Authorization code exchange
    if (code && state) {
      setStatusText('Đang xác thực mã ủy quyền với Google...');
      loginWithGoogle(code, state)
        .then(() => {
          navigate('/', { replace: true });
        })
        .catch((err: any) => {
          setErrorMessage(
            err?.message || 'Xác thực Google không thành công. Vui lòng thử lại.'
          );
        });
      return;
    }

    // 4. Missing required query parameters
    setErrorMessage(
      'Không tìm thấy thông tin xác thực từ Google. Vui lòng thử đăng nhập lại.'
    );
  }, [searchParams, loginWithGoogle, loginWithToken, navigate]);

  return (
    <div className="auth-container">
      <div className="auth-card" style={{ textAlign: 'center', padding: '2.5rem 2rem' }}>
        <div className="auth-header">
          <div className="auth-brand">
            <span>SourceCheck AI</span>
          </div>
          <h1 className="auth-title">
            {errorMessage ? 'Đăng nhập thất bại' : 'Đang đăng nhập'}
          </h1>
        </div>

        {errorMessage ? (
          <div>
            <div className="auth-error-alert" role="alert" style={{ marginBottom: '1.5rem', textAlign: 'left' }}>
              <span>{errorMessage}</span>
            </div>
            <Link to="/login" className="auth-btn-primary" style={{ display: 'inline-flex', justifyContent: 'center', textDecoration: 'none' }}>
              Quay lại trang Đăng nhập
            </Link>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', padding: '1rem 0' }}>
            <div className="spinner spinner-dark" style={{ width: '32px', height: '32px', borderWidth: '3px' }} />
            <p className="auth-subtitle" style={{ margin: 0 }}>
              {statusText}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
