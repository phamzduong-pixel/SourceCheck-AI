/**
 * Shared authentication service for SourceCheck AI.
 * Handles API calls to backend /api/v1/auth endpoints, token persistence, and error parsing.
 */

import {
  APIResponse,
  GoogleLoginResponse,
  LoginCredentials,
  RegisterCredentials,
  TokenResponse,
  User,
  UserProfileUpdate,
} from '../types/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
export const TOKEN_STORAGE_KEY = 'sourcecheck_access_token';

export class AuthApiError extends Error {
  statusCode: number;
  details?: any;

  constructor(message: string, statusCode: number, details?: any) {
    super(message);
    this.name = 'AuthApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

export const getStoredToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
};

export const setStoredToken = (token: string): void => {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // Gracefully handle storage quota or private browsing exceptions
  }
};

export const removeStoredToken = (): void => {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Gracefully handle storage exceptions
  }
};

async function handleResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  const data = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    let errorMessage = 'Đã xảy ra lỗi không xác định.';
    if (data) {
      if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      } else if (Array.isArray(data.detail) && data.detail[0]?.msg) {
        // FastAPI / Pydantic validation error
        errorMessage = data.detail.map((e: any) => e.msg).join(', ');
      } else if (data.message) {
        errorMessage = data.message;
      }
    } else if (response.status === 401) {
      errorMessage = 'Email hoặc mật khẩu không chính xác.';
    } else if (response.status === 404) {
      errorMessage = 'Không tìm thấy API xác thực máy chủ (404).';
    } else if (response.status >= 500) {
      errorMessage = 'Lỗi máy chủ nội bộ. Vui lòng thử lại sau.';
    }

    throw new AuthApiError(errorMessage, response.status, data);
  }

  if (!data) {
    throw new AuthApiError('Phản hồi từ máy chủ không hợp lệ.', response.status);
  }

  // If response is wrapped in standard APIResponse envelope
  if (typeof data === 'object' && 'data' in data && 'success' in data) {
    return (data as APIResponse<T>).data;
  }

  return data as T;
}

export const authService = {
  /**
   * Register a new user account.
   */
  async register(credentials: RegisterCredentials): Promise<User> {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          email: credentials.email.trim().toLowerCase(),
          password: credentials.password,
          full_name: credentials.full_name?.trim() || undefined,
        }),
      });

      return await handleResponse<User>(response);
    } catch (err: any) {
      if (err instanceof AuthApiError) throw err;
      throw new AuthApiError(
        'Không thể kết nối tới máy chủ. Vui lòng kiểm tra đường truyền mạng.',
        0,
        err
      );
    }
  },

  /**
   * Authenticate user with email and password, saving the JWT token.
   */
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          email: credentials.email.trim().toLowerCase(),
          password: credentials.password,
        }),
      });

      const tokenData = await handleResponse<TokenResponse>(response);
      if (tokenData?.access_token) {
        setStoredToken(tokenData.access_token);
      }
      return tokenData;
    } catch (err: any) {
      if (err instanceof AuthApiError) throw err;
      throw new AuthApiError(
        'Không thể kết nối tới máy chủ. Vui lòng kiểm tra đường truyền mạng.',
        0,
        err
      );
    }
  },

  /**
   * Retrieve current user profile using Bearer token.
   */
  async getMe(customToken?: string): Promise<User> {
    const token = customToken || getStoredToken();
    if (!token) {
      throw new AuthApiError('Chưa đăng nhập.', 401);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
      });

      if (response.status === 401) {
        removeStoredToken();
      }

      return await handleResponse<User>(response);
    } catch (err: any) {
      if (err instanceof AuthApiError) throw err;
      throw new AuthApiError(
        'Không thể kết nối tới máy chủ để xác thực phiên làm việc.',
        0,
        err
      );
    }
  },

  /**
   * Update editable fields for the currently authenticated user.
   */
  async updateMe(payload: UserProfileUpdate): Promise<User> {
    const token = getStoredToken();
    if (!token) {
      throw new AuthApiError('Chưa đăng nhập.', 401);
    }
    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      return await handleResponse<User>(response);
    } catch (err: any) {
      if (err instanceof AuthApiError) throw err;
      throw new AuthApiError('Không thể lưu thông tin hồ sơ. Vui lòng thử lại sau.', 0, err);
    }
  },
  /**
   * Request Google OAuth authorization URL from backend.
   */
  async getGoogleAuthUrl(): Promise<string> {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/google/login`, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
      });

      const data = await handleResponse<GoogleLoginResponse>(response);
      return data.authorization_url;
    } catch (err: any) {
      if (err instanceof AuthApiError) throw err;
      throw new AuthApiError(
        'Không thể khởi tạo đăng nhập Google. Vui lòng thử lại sau.',
        0,
        err
      );
    }
  },

  /**
   * Exchange Google authorization code and state for SourceCheck JWT.
   */
  async handleGoogleCallback(code: string, state: string): Promise<TokenResponse> {
    try {
      const params = new URLSearchParams({ code, state });
      const response = await fetch(`${API_BASE_URL}/auth/google/callback?${params.toString()}`, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
      });

      const tokenData = await handleResponse<TokenResponse>(response);
      if (tokenData?.access_token) {
        setStoredToken(tokenData.access_token);
      }
      return tokenData;
    } catch (err: any) {
      if (err instanceof AuthApiError) throw err;
      throw new AuthApiError(
        'Xác thực Google OAuth không thành công.',
        0,
        err
      );
    }
  },

  /**
   * Logout user by clearing stored credentials.
   */
  logout(): void {
    removeStoredToken();
  },
};
