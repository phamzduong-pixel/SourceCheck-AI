/**
 * Centralized API Client for SourceCheck AI.
 * Handles unified HTTP requests, authorization token injection, error parsing,
 * multipart file uploads, and standard API envelope unwrapping.
 */

import { getStoredToken, removeStoredToken } from './auth';
import { APIResponse } from '../types/common';

const DEFAULT_API_BASE_URL = '/api/v1';

export const getApiBaseUrl = (): string => {
  return import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL;
};

export class ApiClientError extends Error {
  statusCode: number;
  errorData?: any;

  constructor(message: string, statusCode: number, errorData?: any) {
    super(message);
    this.name = 'ApiClientError';
    this.statusCode = statusCode;
    this.errorData = errorData;
  }
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  params?: Record<string, string | number | boolean | undefined | null>;
  skipAuth?: boolean;
  rawPath?: boolean; // If true, do not prepend API_BASE_URL (useful for /health, /ready)
}

/**
 * Format and resolve target URL with query parameters.
 */
function buildUrl(path: string, options?: RequestOptions): string {
  let url = path;

  if (!options?.rawPath) {
    const baseUrl = getApiBaseUrl().replace(/\/+$/, '');
    const cleanPath = path.replace(/^\/+/, '');
    url = `${baseUrl}/${cleanPath}`;
  }

  if (options?.params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(options.params)) {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    }
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
  }

  return url;
}

/**
 * Build request headers with content-type and authorization token.
 */
function buildHeaders(
  options?: RequestOptions,
  isMultipart: boolean = false
): Headers {
  const headers = new Headers(options?.headers);

  // Set Accept header if not specified
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  // Set Content-Type only for non-multipart requests (browser sets multipart boundary automatically)
  if (!isMultipart && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  // Inject Authorization Bearer token if available and not skipped
  if (!options?.skipAuth && !headers.has('Authorization')) {
    const token = getStoredToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  return headers;
}

/**
 * Parse and unwrap response JSON, extracting backend error messages when unsuccessful.
 */
async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  const data = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    let errorMessage = 'Đã xảy ra lỗi trong quá trình xử lý yêu cầu.';

    if (data) {
      if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      } else if (Array.isArray(data.detail) && data.detail[0]?.msg) {
        // FastAPI / Pydantic validation error schema
        errorMessage = data.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
      } else if (typeof data.detail === 'object' && data.detail?.message) {
        errorMessage = data.detail.message;
      } else if (data.message) {
        errorMessage = data.message;
      } else if (data.error && typeof data.error === 'object' && data.error.message) {
        errorMessage = data.error.message;
      }
    } else if (response.status === 401) {
      removeStoredToken();
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('sourcecheck:auth-expired'));
      }
      errorMessage = 'Phiên làm việc đã hết hạn hoặc không có quyền truy cập (401).';
    } else if (response.status === 403) {
      errorMessage = 'Bạn không có quyền thực hiện hành động này (403).';
    } else if (response.status === 404) {
      errorMessage = 'Không tìm thấy tài nguyên yêu cầu (404).';
    } else if (response.status >= 500) {
      errorMessage = 'Lỗi máy chủ nội bộ. Vui lòng thử lại sau (500).';
    }

    throw new ApiClientError(errorMessage, response.status, data);
  }

  if (data === null || data === undefined) {
    // If successful but no body (e.g. 204 No Content)
    return null as unknown as T;
  }

  // Check if response is wrapped in standard APIResponse envelope
  if (typeof data === 'object' && 'success' in data && 'data' in data) {
    const apiEnvelope = data as APIResponse<T>;
    if (apiEnvelope.success === false) {
      const errorMsg = apiEnvelope.message || 'Thao tác không thành công.';
      throw new ApiClientError(errorMsg, response.status, apiEnvelope);
    }
    return apiEnvelope.data;
  }

  return data as T;
}

export const apiClient = {
  /**
   * Execute GET request.
   */
  async get<T>(path: string, options?: RequestOptions): Promise<T> {
    const url = buildUrl(path, options);
    const headers = buildHeaders(options);

    try {
      const response = await fetch(url, {
        ...options,
        method: 'GET',
        headers,
      });
      return await parseResponse<T>(response);
    } catch (err: any) {
      if (err instanceof ApiClientError) throw err;
      throw new ApiClientError(
        'Không thể kết nối tới máy chủ. Vui lòng kiểm tra kết nối mạng.',
        0,
        err
      );
    }
  },

  /**
   * Execute POST request with JSON payload.
   */
  async post<T>(path: string, body?: any, options?: RequestOptions): Promise<T> {
    const url = buildUrl(path, options);
    const headers = buildHeaders(options);

    try {
      const response = await fetch(url, {
        ...options,
        method: 'POST',
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
      return await parseResponse<T>(response);
    } catch (err: any) {
      if (err instanceof ApiClientError) throw err;
      throw new ApiClientError(
        'Không thể kết nối tới máy chủ. Vui lòng kiểm tra kết nối mạng.',
        0,
        err
      );
    }
  },

  /**
   * Execute PATCH request with JSON payload.
   */
  async patch<T>(path: string, body?: any, options?: RequestOptions): Promise<T> {
    const url = buildUrl(path, options);
    const headers = buildHeaders(options);

    try {
      const response = await fetch(url, {
        ...options,
        method: 'PATCH',
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
      return await parseResponse<T>(response);
    } catch (err: any) {
      if (err instanceof ApiClientError) throw err;
      throw new ApiClientError(
        'Không thể kết nối tới máy chủ. Vui lòng kiểm tra kết nối mạng.',
        0,
        err
      );
    }
  },

  /**
   * Execute POST request with multipart/form-data for file uploads.
   */
  async upload<T>(
    path: string,
    formData: FormData,
    options?: RequestOptions
  ): Promise<T> {
    const url = buildUrl(path, options);
    const headers = buildHeaders(options, true);

    try {
      const response = await fetch(url, {
        ...options,
        method: 'POST',
        headers,
        body: formData,
      });
      return await parseResponse<T>(response);
    } catch (err: any) {
      if (err instanceof ApiClientError) throw err;
      throw new ApiClientError(
        'Không thể kết nối tới máy chủ khi tải lên tệp tin.',
        0,
        err
      );
    }
  },

  /**
   * Execute DELETE request.
   */
  async delete<T>(path: string, options?: RequestOptions): Promise<T> {
    const url = buildUrl(path, options);
    const headers = buildHeaders(options);

    try {
      const response = await fetch(url, {
        ...options,
        method: 'DELETE',
        headers,
      });
      return await parseResponse<T>(response);
    } catch (err: any) {
      if (err instanceof ApiClientError) throw err;
      throw new ApiClientError(
        'Không thể kết nối tới máy chủ. Vui lòng kiểm tra kết nối mạng.',
        0,
        err
      );
    }
  },
};
