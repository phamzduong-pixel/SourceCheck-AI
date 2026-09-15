/**
 * Authentication and user profile type definitions for SourceCheck AI.
 */

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'user' | 'researcher' | 'admin' | string;
  is_active: boolean;
  avatar_url?: string | null;
  auth_provider?: string;
  created_at: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface GoogleLoginResponse {
  authorization_url: string;
  state: string;
}

export type { APIResponse } from './common';

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}
