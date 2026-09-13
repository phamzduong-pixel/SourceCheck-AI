/**
 * Authentication Context providing centralized state and actions across the application.
 */

import React, { createContext, useCallback, useEffect, useState } from 'react';
import {
  authService,
  getStoredToken,
  setStoredToken,
  removeStoredToken,
} from '../services/auth';
import { LoginCredentials, RegisterCredentials, User } from '../types/auth';

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  loginWithGoogle: (code: string, state: string) => Promise<void>;
  loginWithToken: (token: string) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<User>;
  logout: () => void;
  clearError: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => setError(null), []);

  // Hydrate user profile on initial mount if token exists
  useEffect(() => {
    let isMounted = true;

    const hydrateAuth = async () => {
      const storedToken = getStoredToken();
      if (!storedToken) {
        if (isMounted) {
          setIsLoading(false);
          setUser(null);
          setToken(null);
        }
        return;
      }

      try {
        const currentUser = await authService.getMe(storedToken);
        if (isMounted) {
          setUser(currentUser);
          setToken(storedToken);
        }
      } catch {
        if (isMounted) {
          removeStoredToken();
          setUser(null);
          setToken(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    hydrateAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    setIsLoading(true);
    setError(null);
    try {
      const tokenResp = await authService.login(credentials);
      setToken(tokenResp.access_token);
      // Fetch full user profile
      const userProfile = await authService.getMe(tokenResp.access_token);
      setUser(userProfile);
    } catch (err: any) {
      const msg = err?.message || 'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.';
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loginWithGoogle = useCallback(async (code: string, state: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const tokenResp = await authService.handleGoogleCallback(code, state);
      setToken(tokenResp.access_token);
      const userProfile = await authService.getMe(tokenResp.access_token);
      setUser(userProfile);
    } catch (err: any) {
      const msg = err?.message || 'Đăng nhập Google thất bại.';
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loginWithToken = useCallback(async (customToken: string) => {
    setIsLoading(true);
    setError(null);
    try {
      setStoredToken(customToken);
      setToken(customToken);
      const userProfile = await authService.getMe(customToken);
      setUser(userProfile);
    } catch (err: any) {
      removeStoredToken();
      setToken(null);
      setUser(null);
      const msg = err?.message || 'Token xác thực không hợp lệ.';
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (credentials: RegisterCredentials) => {
    setIsLoading(true);
    setError(null);
    try {
      const createdUser = await authService.register(credentials);
      return createdUser;
    } catch (err: any) {
      const msg = err?.message || 'Đăng ký tài khoản thất bại.';
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
    setToken(null);
    setError(null);
  }, []);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: Boolean(user && token),
    isLoading,
    error,
    login,
    loginWithGoogle,
    loginWithToken,
    register,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
