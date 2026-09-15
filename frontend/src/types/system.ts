/**
 * System Health and Readiness check types matching backend app.api.routers.health.
 */

export interface HealthCheckResponse {
  status: string;
  service: string;
  environment: string;
}

export interface ReadinessCheckResponse {
  status: string;
  database: string;
  redis: string;
  vector_db: string;
}
