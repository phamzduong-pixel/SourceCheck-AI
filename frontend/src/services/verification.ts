/**
 * Fact-Checking Verification service.
 * Endpoints: /api/v1/verify/*
 */

import { apiClient } from './apiClient';
import {
  ClaimExtractRequest,
  ClaimExtractResponse,
  VerificationCreateRequest,
  VerificationResultResponse,
} from '../types/verification';

export const verificationService = {
  /**
   * Execute full fact-checking verification pipeline.
   * Endpoint: POST /api/v1/verify
   */
  async verifyText(request: VerificationCreateRequest): Promise<VerificationResultResponse> {
    return apiClient.post<VerificationResultResponse>('/verify', request);
  },

  /**
   * Extract verifiable factual claims from input text.
   * Endpoint: POST /api/v1/verify/extract-claims
   */
  async extractClaims(request: ClaimExtractRequest): Promise<ClaimExtractResponse> {
    return apiClient.post<ClaimExtractResponse>('/verify/extract-claims', request);
  },

  /**
   * Retrieve historical verification report by request ID.
   * Endpoint: GET /api/v1/verify/{request_id}
   */
  async getVerificationReport(requestId: string): Promise<VerificationResultResponse> {
    return apiClient.get<VerificationResultResponse>(`/verify/${requestId}`);
  },
};
