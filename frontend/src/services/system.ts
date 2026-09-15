/**
 * System and Health service for monitoring backend connectivity.
 */

import { apiClient } from './apiClient';
import { HealthCheckResponse, ReadinessCheckResponse } from '../types/system';

export const systemService = {
  /**
   * Check backend liveness.
   * Endpoint: GET /health
   */
  async getHealth(): Promise<HealthCheckResponse> {
    return apiClient.get<HealthCheckResponse>('/health', { rawPath: true, skipAuth: true });
  },

  /**
   * Check backend readiness (Postgres, Redis, pgvector).
   * Endpoint: GET /ready
   */
  async getReadiness(): Promise<ReadinessCheckResponse> {
    return apiClient.get<ReadinessCheckResponse>('/ready', { rawPath: true, skipAuth: true });
  },
};
