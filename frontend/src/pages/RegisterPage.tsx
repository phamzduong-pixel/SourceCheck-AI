/**
 * RegisterPage: Minimalist, clean, modern registration interface for SourceCheck AI.
 */

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useAIPreferences } from '../hooks/useAIPreferences';
import { GoogleButton } from '../components/auth/GoogleButton';
import { EyeIcon } from '../components/auth/EyeIcon';
import { authService } from '../services/auth';
import '../styles/auth.css';

export const RegisterPage: React.FC = () => {
  const { t } = useAIPreferences();
  const { register, login, error: authError, clearError } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

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

    // Email regex format check
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(trimmedEmail)) {
      setLocalError('Định dạng email không hợp lệ.');
      return;
    }

    if (!password) {
      setLocalError('Vui lòng nhập mật khẩu.');
      return;
    }

    if (password.length < 6) {
      setLocalError('Mật khẩu phải có tối thiểu 6 ký tự.');
      return;
    }

    if (password !== confirmPassword) {
      setLocalError('Mật khẩu xác nhận không khớp.');
      return;
    }

    setIsSubmitting(true);
    try {
      // 1. Register account
      await register({ email: trimmedEmail, password });
      // 2. Automatically log in upon successful registration
      await login({ email: trimmedEmail, password });
      navigate('/', { replace: true });
    } catch (err: any) {
      setLocalError(err?.message || 'Đăng ký tài khoản thất bại.');
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
          <h1 className="auth-title">{t('auth.createTitle')}</h1>
          <p className="auth-subtitle">Đăng ký để sử dụng nền tảng kiểm chứng</p>
        </div>

        {displayError && (
          <div className="auth-error-alert" role="alert" style={{ marginBottom: '1.25rem' }}>
            <span>{displayError}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="register-email">
              {t('auth.email')}
            </label>
            <input
              id="register-email"
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
            <label className="form-label" htmlFor="register-password">
              {t('auth.password')}
            </label>
            <div className="form-input-wrapper">
              <input
                id="register-password"
                type={showPassword ? 'text' : 'password'}
                className={`form-input ${displayError ? 'has-error' : ''}`}
                placeholder="Tối thiểu 6 ký tự"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting}
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
              >
                <EyeIcon visible={showPassword} />
              </button>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="register-confirm-password">
              {t('auth.confirmPassword')}
            </label>
            <div className="form-input-wrapper">
              <input
                id="register-confirm-password"
                type={showConfirmPassword ? 'text' : 'password'}
                className={`form-input ${displayError ? 'has-error' : ''}`}
                placeholder="Nhập lại mật khẩu"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isSubmitting}
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                aria-label={showConfirmPassword ? t('auth.hidePassword') : t('auth.showPassword')}
              >
                <EyeIcon visible={showConfirmPassword} />
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
                <span>{t('auth.creatingAccount')}</span>
              </>
            ) : (
              t('auth.createAccount')
            )}
          </button>
        </form>

        <div className="auth-divider">
          <span>{t('auth.or')}</span>
        </div>

        <GoogleButton
          onClick={handleGoogleLogin}
          isLoading={isGoogleLoading}
          disabled={isSubmitting}
        />

        <div className="auth-footer">
          <span>{t('auth.alreadyAccount')}</span>
          <Link to="/login" className="auth-link">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
};
