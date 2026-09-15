/**
 * Common API Response and Pagination schemas matching backend app.schemas.common.
 */

export interface APIResponse<T = any> {
  success: boolean;
  data: T;
  message?: string | null;
  error?: {
    code?: string;
    message?: string;
    details?: any;
  } | null;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
