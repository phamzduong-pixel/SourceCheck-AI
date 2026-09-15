/**
 * Test Suite for Dashboard & System Overview (FE-04.9).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from '../pages/DashboardPage';
import { dashboardService } from '../services/dashboard';
import { ApiClientError } from '../services/apiClient';
import { DashboardStats } from '../types/dashboard';

const mockPopulatedStats: DashboardStats = {
  total_documents: 14,
  total_chunks: 182,
  total_questions: 45,
  total_conversations: 20,
  total_verifications: 28,
  total_claims_verified: 80,
  verification_distribution: {
    supported: 40,
    partially_supported: 16,
    refuted: 16,
    not_enough_info: 8,
  },
  recent_activity: [
    {
      id: 'act-1',
      type: 'document',
      title: 'Tài liệu: Nghị định số 13/2023/NĐ-CP',
      description: 'Loại: PDF',
      status: 'INGESTED',
      created_at: '2026-09-15T08:30:00Z',
      metadata: { doc_type: 'pdf' },
    },
    {
      id: 'act-2',
      type: 'question',
      title: 'Hỏi đáp: Tốc độ tăng trưởng GDP 2024 của Việt Nam...',
      description: 'Tốc độ tăng trưởng GDP 2024 của Việt Nam đạt bao nhiêu?',
      status: 'ANSWERED',
      created_at: '2026-09-15T09:15:00Z',
    },
    {
      id: 'act-3',
      type: 'verification',
      title: 'Kiểm chứng: SJC vượt 90 triệu đồng...',
      description: 'Giá vàng SJC vượt 90 triệu đồng vào tháng 5/2024.',
      status: 'TRUE',
      created_at: '2026-09-15T10:00:00Z',
    },
    {
      id: 'act-4',
      type: 'conversation',
      title: 'Tra cứu: Quy định an ninh mạng',
      description: 'Quy định an ninh mạng',
      status: 'ACTIVE',
      created_at: '2026-09-15T10:30:00Z',
    },
  ],
  evaluation_summary: {
    run_name: 'benchmark_v2_exp',
    dataset_name: 'vietnamese_rag_bench',
    metrics_summary: {
      faithfulness: 0.945,
      evidence_recall: 0.912,
      latency_ms: 320,
    },
    created_at: '2026-09-14T12:00:00Z',
  },
};

const mockEmptyStats: DashboardStats = {
  total_documents: 0,
  total_chunks: 0,
  total_questions: 0,
  total_conversations: 0,
  total_verifications: 0,
  total_claims_verified: 0,
  verification_distribution: {
    supported: 0,
    partially_supported: 0,
    refuted: 0,
    not_enough_info: 0,
  },
  recent_activity: [],
  evaluation_summary: null,
};

const mockHealthResponse = {
  status: 'healthy' as const,
  version: '0.1.0',
  environment: 'development',
  timestamp: '2026-09-15T12:00:00Z',
  components: {
    backend_api: {
      status: 'healthy' as const,
      latency_ms: 0.5,
      details: 'SourceCheck AI FastAPI service active',
    },
    postgresql: {
      status: 'healthy' as const,
      latency_ms: 2.1,
      details: 'Primary database connected',
    },
    pgvector: {
      status: 'healthy' as const,
      latency_ms: 1.8,
      details: 'pgvector extension enabled',
    },
    llm_service: {
      status: 'healthy' as const,
      latency_ms: null,
      details: 'OpenAI (gpt-4o-mini) - Configured',
    },
    embedding_service: {
      status: 'healthy' as const,
      latency_ms: 1.2,
      details: 'openai provider (text-embedding-3-small, dim=1536)',
    },
    reranker_service: {
      status: 'healthy' as const,
      latency_ms: 1.5,
      details: 'Reranker active (cross_encoder - BAAI/bge-reranker-base)',
    },
  },
};

describe('Dashboard & System Overview (FE-04.9)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(dashboardService, 'getHealthDetails').mockResolvedValue(mockHealthResponse);
  });

  const renderDashboard = () => {
    return render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
  };

  it('1. Initial Load: renders loading skeleton initially while fetching metrics', async () => {
    let resolvePromise: (value: DashboardStats) => void;
    const pendingPromise = new Promise<DashboardStats>((resolve) => {
      resolvePromise = resolve;
    });

    vi.spyOn(dashboardService, 'getStats').mockReturnValue(pendingPromise);

    renderDashboard();

    expect(screen.getByTestId('dashboard-loading-skeleton')).toBeInTheDocument();

    // Resolve API
    resolvePromise!(mockPopulatedStats);

    await waitFor(() => {
      expect(screen.queryByTestId('dashboard-loading-skeleton')).not.toBeInTheDocument();
      expect(screen.getByTestId('dashboard-summary-cards')).toBeInTheDocument();
    });
  });

  it('2. API Success & Summary Data: displays all aggregated metrics correctly', async () => {
    vi.spyOn(dashboardService, 'getStats').mockResolvedValue(mockPopulatedStats);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-summary-cards')).toBeInTheDocument();
    });

    // Verify summary card values
    expect(screen.getByTestId('stat-documents-value')).toHaveTextContent('14');
    expect(screen.getByTestId('stat-chunks-value')).toHaveTextContent('182');
    expect(screen.getByTestId('stat-questions-value')).toHaveTextContent('45');
    expect(screen.getByTestId('stat-conversations-value')).toHaveTextContent('20');
    expect(screen.getByTestId('stat-verifications-value')).toHaveTextContent('28');
    expect(screen.getByTestId('stat-claims-value')).toHaveTextContent('80');
  });

  it('3. Verification Distribution: computes and renders correct percentages and bars', async () => {
    vi.spyOn(dashboardService, 'getStats').mockResolvedValue(mockPopulatedStats);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('verification-distribution-card')).toBeInTheDocument();
    });

    // Total = 40 + 16 + 16 + 8 = 80
    // Supported: 40 / 80 = 50%
    // Partially: 16 / 80 = 20%
    // Refuted: 16 / 80 = 20%
    // Not enough info: 8 / 80 = 10%
    expect(screen.getByTestId('dist-count-supported')).toHaveTextContent('40');
    expect(screen.getByTestId('dist-bar-supported')).toHaveStyle({ width: '50%' });

    expect(screen.getByTestId('dist-count-partially-supported')).toHaveTextContent('16');
    expect(screen.getByTestId('dist-bar-partially-supported')).toHaveStyle({ width: '20%' });

    expect(screen.getByTestId('dist-count-refuted')).toHaveTextContent('16');
    expect(screen.getByTestId('dist-bar-refuted')).toHaveStyle({ width: '20%' });

    expect(screen.getByTestId('dist-count-not-enough-info')).toHaveTextContent('8');
    expect(screen.getByTestId('dist-bar-not-enough-info')).toHaveStyle({ width: '10%' });
  });

  it('4. Benchmark Evaluation Banner: renders when evaluation data is present', async () => {
    vi.spyOn(dashboardService, 'getStats').mockResolvedValue(mockPopulatedStats);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('eval-run-banner')).toBeInTheDocument();
    });

    expect(screen.getByText(/benchmark_v2_exp/i)).toBeInTheDocument();
    expect(screen.getByText('94.5%')).toBeInTheDocument();
    expect(screen.getByText('91.2%')).toBeInTheDocument();
  });

  it('5. Recent Activity: renders timeline items with correct badges and types', async () => {
    vi.spyOn(dashboardService, 'getStats').mockResolvedValue(mockPopulatedStats);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('activity-feed-list')).toBeInTheDocument();
    });

    expect(screen.getByTestId('activity-item-act-1')).toHaveTextContent(/Nghị định số 13/i);
    expect(screen.getByTestId('activity-item-act-2')).toHaveTextContent(/Tăng trưởng GDP/i);
    expect(screen.getByTestId('activity-item-act-3')).toHaveTextContent(/SJC vượt 90 triệu/i);
    expect(screen.getByTestId('activity-item-act-4')).toHaveTextContent(/Quy định an ninh mạng/i);
  });

  it('6. Empty State: renders empty notices when system has zero data', async () => {
    vi.spyOn(dashboardService, 'getStats').mockResolvedValue(mockEmptyStats);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-empty-notice')).toBeInTheDocument();
      expect(screen.getByTestId('recent-activity-empty')).toBeInTheDocument();
    });

    expect(screen.getByTestId('stat-documents-value')).toHaveTextContent('0');
    expect(screen.queryByTestId('eval-run-banner')).not.toBeInTheDocument();
  });

  it('7. API Error Handling & Retry: displays error banner and recovers on retry', async () => {
    const getStatsMock = vi
      .spyOn(dashboardService, 'getStats')
      .mockRejectedValueOnce(new ApiClientError('Không thể kết nối tới cơ sở dữ liệu.', 500))
      .mockResolvedValueOnce(mockPopulatedStats);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-error-banner')).toBeInTheDocument();
    });

    expect(screen.getByText(/Không thể kết nối tới cơ sở dữ liệu/i)).toBeInTheDocument();

    // Click retry
    fireEvent.click(screen.getByTestId('btn-dashboard-retry'));

    await waitFor(() => {
      expect(screen.queryByTestId('dashboard-error-banner')).not.toBeInTheDocument();
      expect(screen.getByTestId('dashboard-summary-cards')).toBeInTheDocument();
    });

    expect(getStatsMock).toHaveBeenCalledTimes(2);
  });

  it('8. Manual Refresh: re-triggers getStats with manual refresh indicator', async () => {
    const getStatsMock = vi.spyOn(dashboardService, 'getStats').mockResolvedValue(mockPopulatedStats);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-summary-cards')).toBeInTheDocument();
    });

    const refreshBtn = screen.getByTestId('btn-dashboard-refresh');
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(getStatsMock).toHaveBeenCalledTimes(2);
    });
  });

  it('9. Navigation & Quick Actions: renders 4 core modules links (/qa, /fact-check, /documents, /search)', async () => {
    vi.spyOn(dashboardService, 'getStats').mockResolvedValue(mockPopulatedStats);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-quick-actions')).toBeInTheDocument();
    });

    expect(screen.getByTestId('card-qa')).toHaveAttribute('href', '/qa');
    expect(screen.getByTestId('card-fact-check')).toHaveAttribute('href', '/fact-check');
    expect(screen.getByTestId('card-documents')).toHaveAttribute('href', '/documents');
    expect(screen.getByTestId('card-search')).toHaveAttribute('href', '/search');
  });

  it('10. Dark Mode Compatibility: elements adapt to dark mode attributes without error', async () => {
    document.documentElement.setAttribute('data-theme', 'dark');

    vi.spyOn(dashboardService, 'getStats').mockResolvedValue(mockPopulatedStats);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    document.documentElement.removeAttribute('data-theme');
  });

  it('11. System Health: renders system health card with all 6 dependency badges', async () => {
    vi.spyOn(dashboardService, 'getStats').mockResolvedValue(mockPopulatedStats);
    vi.spyOn(dashboardService, 'getHealthDetails').mockResolvedValue(mockHealthResponse);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('system-health-card')).toBeInTheDocument();
    });

    expect(screen.getByTestId('health-overall-status')).toHaveTextContent(/Hoạt động tốt/i);
    expect(screen.getByTestId('health-component-backend_api')).toBeInTheDocument();
    expect(screen.getByTestId('health-component-postgresql')).toBeInTheDocument();
    expect(screen.getByTestId('health-component-pgvector')).toBeInTheDocument();
    expect(screen.getByTestId('health-component-llm_service')).toBeInTheDocument();
    expect(screen.getByTestId('health-component-embedding_service')).toBeInTheDocument();
    expect(screen.getByTestId('health-component-reranker_service')).toBeInTheDocument();

    expect(screen.getByTestId('health-last-checked')).toHaveTextContent(/Kiểm tra lúc/i);
  });

  it('12. System Health: handles degraded dependencies gracefully without failing dashboard', async () => {
    vi.spyOn(dashboardService, 'getStats').mockResolvedValue(mockPopulatedStats);
    vi.spyOn(dashboardService, 'getHealthDetails').mockResolvedValue({
      status: 'degraded',
      version: '0.1.0',
      environment: 'development',
      timestamp: '2026-09-15T12:00:00Z',
      components: {
        backend_api: {
          status: 'healthy',
          latency_ms: 0.5,
          details: 'Active',
        },
        postgresql: {
          status: 'degraded',
          latency_ms: 15.0,
          details: 'Fallback to local SQLite database',
        },
      },
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('system-health-card')).toBeInTheDocument();
    });

    expect(screen.getByTestId('health-overall-status')).toHaveTextContent(/Đang suy giảm/i);
    expect(screen.getByTestId('health-badge-postgresql')).toHaveTextContent(/Đang suy giảm/i);
    expect(screen.getByTestId('health-detail-postgresql')).toHaveTextContent(/Fallback to local SQLite/i);
  });
});
