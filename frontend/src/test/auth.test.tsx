/**
 * Frontend Authentication Test Suite for SourceCheck AI.
 * Tests Login, Register, validation, AuthContext, ProtectedRoute, and Logout.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { OAuthCallbackPage } from '../pages/OAuthCallbackPage';
import { ProtectedPlaceholderPage } from '../pages/ProtectedPlaceholderPage';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { TOKEN_STORAGE_KEY } from '../services/auth';

describe('Authentication Pages & Routing', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  describe('1. LoginPage UI & Interactions', () => {
    it('renders login page with brand, title, inputs, and submit button', () => {
      render(
        <MemoryRouter>
          <AuthProvider>
            <LoginPage />
          </AuthProvider>
        </MemoryRouter>
      );

      expect(screen.getByText('SourceCheck AI')).toBeInTheDocument();
      expect(screen.getByText('Welcome back')).toBeInTheDocument();
      expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument();
      expect(screen.getByText(/create account/i)).toBeInTheDocument();
    });

    it('validates empty inputs on submit', async () => {
      render(
        <MemoryRouter>
          <AuthProvider>
            <LoginPage />
          </AuthProvider>
        </MemoryRouter>
      );

      const submitBtn = screen.getByRole('button', { name: /sign in/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(screen.getByText(/vui lòng nhập địa chỉ email/i)).toBeInTheDocument();
      });
    });

    it('toggles password visibility between password and text', () => {
      render(
        <MemoryRouter>
          <AuthProvider>
            <LoginPage />
          </AuthProvider>
        </MemoryRouter>
      );

      const passwordInput = screen.getByLabelText(/^password$/i) as HTMLInputElement;
      const toggleBtn = screen.getByRole('button', { name: /show password/i });

      expect(passwordInput.type).toBe('password');
      fireEvent.click(toggleBtn);
      expect(passwordInput.type).toBe('text');
      fireEvent.click(toggleBtn);
      expect(passwordInput.type).toBe('password');
    });

    it('handles login failure (e.g. 401) and displays error message', async () => {
      // Mock fetch failure
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Email hoặc mật khẩu không chính xác.' }),
      } as Response);

      render(
        <MemoryRouter>
          <AuthProvider>
            <LoginPage />
          </AuthProvider>
        </MemoryRouter>
      );

      fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: 'user@example.com' } });
      fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'wrongpass' } });
      fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(screen.getByText('Email hoặc mật khẩu không chính xác.')).toBeInTheDocument();
      });
    });

    it('handles successful login and stores JWT token in localStorage', async () => {
      // Mock login endpoint
      vi.spyOn(globalThis, 'fetch')
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            data: { access_token: 'fake-jwt-token-123', token_type: 'bearer', expires_in: 86400 },
          }),
        } as Response)
        // Mock getMe endpoint
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            data: {
              id: 'u-1',
              email: 'valid@example.com',
              full_name: 'Valid User',
              role: 'user',
              is_active: true,
              created_at: '2026-09-14T00:00:00Z',
            },
          }),
        } as Response);

      render(
        <MemoryRouter initialEntries={['/login']}>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/" element={<div data-testid="dashboard">Dashboard Area</div>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      );

      fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: 'valid@example.com' } });
      fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'CorrectPass123' } });
      fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBe('fake-jwt-token-123');
        expect(screen.getByTestId('dashboard')).toBeInTheDocument();
      });
    });
  });

  describe('2. RegisterPage UI & Validation', () => {
    it('renders register page with brand, title, and confirm password field', () => {
      render(
        <MemoryRouter>
          <AuthProvider>
            <RegisterPage />
          </AuthProvider>
        </MemoryRouter>
      );

      expect(screen.getByText('SourceCheck AI')).toBeInTheDocument();
      expect(screen.getByText('Create your account')).toBeInTheDocument();
      expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^confirm password$/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument();
      expect(screen.getByText(/sign in/i)).toBeInTheDocument();
    });

    it('rejects invalid email formats on register', async () => {
      render(
        <MemoryRouter>
          <AuthProvider>
            <RegisterPage />
          </AuthProvider>
        </MemoryRouter>
      );

      fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: 'invalid-email-format' } });
      fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'Password123' } });
      fireEvent.change(screen.getByLabelText(/^confirm password$/i), { target: { value: 'Password123' } });
      fireEvent.click(screen.getByRole('button', { name: /create account/i }));

      await waitFor(() => {
        expect(screen.getByText(/định dạng email không hợp lệ/i)).toBeInTheDocument();
      });
    });

    it('rejects passwords shorter than 6 characters', async () => {
      render(
        <MemoryRouter>
          <AuthProvider>
            <RegisterPage />
          </AuthProvider>
        </MemoryRouter>
      );

      fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: 'test@example.com' } });
      fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: '123' } });
      fireEvent.change(screen.getByLabelText(/^confirm password$/i), { target: { value: '123' } });
      fireEvent.click(screen.getByRole('button', { name: /create account/i }));

      await waitFor(() => {
        expect(screen.getByText(/tối thiểu 6 ký tự/i)).toBeInTheDocument();
      });
    });

    it('rejects mismatched passwords', async () => {
      render(
        <MemoryRouter>
          <AuthProvider>
            <RegisterPage />
          </AuthProvider>
        </MemoryRouter>
      );

      fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: 'test@example.com' } });
      fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'Password123' } });
      fireEvent.change(screen.getByLabelText(/^confirm password$/i), { target: { value: 'DifferentPassword' } });
      fireEvent.click(screen.getByRole('button', { name: /create account/i }));

      await waitFor(() => {
        expect(screen.getByText(/mật khẩu xác nhận không khớp/i)).toBeInTheDocument();
      });
    });

    it('handles duplicate email error from backend', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: false,
        status: 400,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Email đã được đăng ký trong hệ thống.' }),
      } as Response);

      render(
        <MemoryRouter>
          <AuthProvider>
            <RegisterPage />
          </AuthProvider>
        </MemoryRouter>
      );

      fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: 'existing@example.com' } });
      fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'Password123' } });
      fireEvent.change(screen.getByLabelText(/^confirm password$/i), { target: { value: 'Password123' } });
      fireEvent.click(screen.getByRole('button', { name: /create account/i }));

      await waitFor(() => {
        expect(screen.getByText('Email đã được đăng ký trong hệ thống.')).toBeInTheDocument();
      });
    });
  });

  describe('3. Protected Routing & Logout', () => {
    it('redirects unauthenticated users from protected route to /login', async () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <AuthProvider>
            <Routes>
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <ProtectedPlaceholderPage />
                  </ProtectedRoute>
                }
              />
              <Route path="/login" element={<div data-testid="login-screen">Login Screen</div>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('login-screen')).toBeInTheDocument();
      });
    });

    it('renders protected page for authenticated users and allows logout', async () => {
      // Seed token in localStorage
      localStorage.setItem(TOKEN_STORAGE_KEY, 'valid-token');

      // Mock getMe returning user
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          success: true,
          data: {
            id: 'auth-u1',
            email: 'auth_user@example.com',
            full_name: 'Authed User',
            role: 'researcher',
            is_active: true,
            created_at: '2026-09-14T00:00:00Z',
          },
        }),
      } as Response);

      render(
        <MemoryRouter initialEntries={['/']}>
          <AuthProvider>
            <Routes>
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <ProtectedPlaceholderPage />
                  </ProtectedRoute>
                }
              />
              <Route path="/login" element={<div data-testid="login-screen">Login Screen</div>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      );

      // Verify authenticated workspace rendered
      await waitFor(() => {
        expect(screen.getByText('Authenticated Workspace')).toBeInTheDocument();
        expect(screen.getByText('auth_user@example.com')).toBeInTheDocument();
        expect(screen.getByText('Authed User')).toBeInTheDocument();
      });

      // Click Sign out
      const logoutBtn = screen.getByRole('button', { name: /sign out/i });
      fireEvent.click(logoutBtn);

      await waitFor(() => {
        expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
        expect(screen.getByTestId('login-screen')).toBeInTheDocument();
      });
    });
  });

  describe('4. Google OAuth Flow & Callback', () => {
    it('displays user cancellation message when error is access_denied', async () => {
      render(
        <MemoryRouter initialEntries={['/auth/callback?error=access_denied']}>
          <AuthProvider>
            <OAuthCallbackPage />
          </AuthProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Đăng nhập thất bại')).toBeInTheDocument();
        expect(
          screen.getByText(/bạn đã hủy quá trình đăng nhập bằng google/i)
        ).toBeInTheDocument();
        expect(
          screen.getByRole('link', { name: /quay lại trang đăng nhập/i })
        ).toBeInTheDocument();
      });
    });

    it('displays error when callback has no parameters', async () => {
      render(
        <MemoryRouter initialEntries={['/auth/callback']}>
          <AuthProvider>
            <OAuthCallbackPage />
          </AuthProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Đăng nhập thất bại')).toBeInTheDocument();
        expect(
          screen.getByText(/không tìm thấy thông tin xác thực/i)
        ).toBeInTheDocument();
        expect(
          screen.getByRole('link', { name: /quay lại trang đăng nhập/i })
        ).toBeInTheDocument();
      });
    });

    it('exchanges authorization code and state for token and redirects', async () => {
      vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
        const url = String(input);
        if (url.includes('/auth/google/callback')) {
          return {
            ok: true,
            status: 200,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({
              success: true,
              data: {
                access_token: 'google_jwt_token_999',
                token_type: 'bearer',
                expires_in: 3600,
              },
            }),
          } as Response;
        }
        if (url.includes('/auth/me')) {
          return {
            ok: true,
            status: 200,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({
              success: true,
              data: {
                id: 'google-user-999',
                email: 'guser@example.com',
                full_name: 'Google User',
                role: 'user',
                is_active: true,
                created_at: new Date().toISOString(),
              },
            }),
          } as Response;
        }
        return {
          ok: false,
          status: 404,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'Not found' }),
        } as Response;
      });

      render(
        <MemoryRouter initialEntries={['/auth/callback?code=authcode123&state=state456']}>
          <AuthProvider>
            <Routes>
              <Route path="/auth/callback" element={<OAuthCallbackPage />} />
              <Route path="/" element={<div data-testid="authed-destination">Protected Area</div>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('authed-destination')).toBeInTheDocument();
        expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBe('google_jwt_token_999');
      });
    });

    it('handles direct token parameter and logs user in', async () => {
      vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
        const url = String(input);
        if (url.includes('/auth/me')) {
          return {
            ok: true,
            status: 200,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({
              success: true,
              data: {
                id: 'direct-user-888',
                email: 'direct@example.com',
                full_name: 'Direct User',
                role: 'user',
                is_active: true,
                created_at: new Date().toISOString(),
              },
            }),
          } as Response;
        }
        return {
          ok: false,
          status: 404,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'Not found' }),
        } as Response;
      });

      render(
        <MemoryRouter initialEntries={['/auth/callback?token=direct_token_xyz']}>
          <AuthProvider>
            <Routes>
              <Route path="/auth/callback" element={<OAuthCallbackPage />} />
              <Route path="/" element={<div data-testid="authed-destination">Protected Area</div>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('authed-destination')).toBeInTheDocument();
        expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBe('direct_token_xyz');
      });
    });
  });
});
