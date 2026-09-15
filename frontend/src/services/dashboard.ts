/**
 * Dashboard API service for fetching aggregated system statistics.
 */

import { apiClient } from './apiClient';
import { DashboardStats, SystemHealthResponse } from '../types/dashboard';

export const dashboardService = {
  /**
   * Fetch aggregated system statistics for the overview dashboard.
   */
  async getStats(): Promise<DashboardStats> {
    return await apiClient.get<DashboardStats>('/dashboard/stats', {
      params: { _t: Date.now() },
    });
  },

  /**
   * Fetch real-time system health and dependency monitoring status.
   */
  async getHealthDetails(): Promise<SystemHealthResponse> {
    return await apiClient.get<SystemHealthResponse>('/health/details', {
      params: { _t: Date.now() },
    });
  },
};
