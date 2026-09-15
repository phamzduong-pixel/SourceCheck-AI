/**
 * Dashboard API service for fetching aggregated system statistics.
 */

import { apiClient } from './apiClient';
import { DashboardStats } from '../types/dashboard';

export const dashboardService = {
  /**
   * Fetch aggregated system statistics for the overview dashboard.
   */
  async getStats(): Promise<DashboardStats> {
    return await apiClient.get<DashboardStats>('/dashboard/stats');
  },
};
