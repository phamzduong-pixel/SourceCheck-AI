/**
 * Types for the System Overview & Dashboard.
 */

export interface VerificationDistribution {
  supported: number;
  partially_supported: number;
  refuted: number;
  not_enough_info: number;
}

export interface RecentActivityItem {
  id: string;
  type: 'document' | 'question' | 'verification' | 'conversation';
  title: string;
  description?: string;
  status?: string;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface EvaluationSummary {
  run_name: string;
  dataset_name: string;
  metrics_summary?: Record<string, any>;
  created_at: string;
}

export interface DashboardStats {
  total_documents: number;
  total_chunks: number;
  total_questions: number;
  total_conversations: number;
  total_verifications: number;
  total_claims_verified: number;
  verification_distribution: VerificationDistribution;
  recent_activity: RecentActivityItem[];
  evaluation_summary?: EvaluationSummary | null;
}

export type HealthStatus = 'healthy' | 'degraded' | 'unavailable' | 'unknown';

export interface DependencyHealth {
  status: HealthStatus;
  latency_ms?: number | null;
  details?: string | null;
}

export interface SystemHealthResponse {
  status: HealthStatus;
  version: string;
  environment: string;
  timestamp: string;
  components: Record<string, DependencyHealth>;
}
