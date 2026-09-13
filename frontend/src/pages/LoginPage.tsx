/**
 * LoginPage: Minimalist, clean, modern login interface for SourceCheck AI.
 */

import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { GoogleButton } from '../components/auth/GoogleButton';
import { EyeIcon } from '../components/auth/EyeIcon';
import { authService } from '../services/auth';
import '../styles/auth.css';

export const LoginPage: React.FC = () => {
  const { login, error: authError, clearError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  // Where to navigate after successful login
  const from = (location.state as any)?.from?.pathname || '/';

  const handleGoogleLogin = async () => {
    setLocalError(null);
    clearError();
    setIsGoogleLoading(true);
    try {
      const authUrl = await authService.getGoogleAuthUrl();
      window.location.href = authUrl;
    } catch (err: any) {
      setLocalError(err?.message || 'Không thể kết nối đến máy chủ Google.');
      setIsGoogleLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setLocalError('Vui lòng nhập địa chỉ email.');
      return;
    }

    if (!password) {
      setLocalError('Vui lòng nhập mật khẩu.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login({ email: trimmedEmail, password });
      navigate(from, { replace: true });
    } catch (err: any) {
      // Error handled in AuthContext and rendered via authError/localError
      setLocalError(err?.message || 'Đăng nhập không thành công.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const displayError = localError || authError;

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-brand">
            <span>SourceCheck AI</span>
          </div>
          <h1 className="auth-title">Welcome back</h1>
          <p className="auth-subtitle">Nhập thông tin tài khoản để tiếp tục</p>
        </div>

        {displayError && (
          <div className="auth-error-alert" role="alert" style={{ marginBottom: '1.25rem' }}>
            <span>{displayError}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="email-input">
              Email
            </label>
            <input
              id="email-input"
              type="email"
              className={`form-input ${displayError ? 'has-error' : ''}`}
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isSubmitting}
              autoComplete="email"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password-input">
              Password
            </label>
            <div className="form-input-wrapper">
              <input
                id="password-input"
                type={showPassword ? 'text' : 'password'}
                className={`form-input ${displayError ? 'has-error' : ''}`}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                <EyeIcon visible={showPassword} />
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="auth-btn-primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="spinner" />
                <span>Signing in...</span>
              </>
            ) : (
              'Sign in'
            )}
          </button>
        </form>

        <div className="auth-divider">
          <span>or</span>
        </div>

        <GoogleButton
          onClick={handleGoogleLogin}
          isLoading={isGoogleLoading}
          disabled={isSubmitting}
        />

        <div className="auth-footer">
          <span>Don't have an account?</span>
          <Link to="/register" className="auth-link">
            Create account
          </Link>
        </div>
      </div>
    </div>
  );
};
