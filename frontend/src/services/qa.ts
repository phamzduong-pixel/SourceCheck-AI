/**
 * Grounded Question Answering service.
 * Endpoint: /api/v1/questions/*
 */

import { apiClient } from './apiClient';
import { FinalAnswerResponse, QuestionRequest } from '../types/qa';

export const qaService = {
  /**
   * Ask a question and receive a fully verified, grounded answer with citations.
   * Endpoint: POST /api/v1/questions/ask
   *
   * Requires: Bearer Authentication
   */
  async askQuestion(request: QuestionRequest): Promise<FinalAnswerResponse> {
    return apiClient.post<FinalAnswerResponse>('/questions/ask', request);
  },
};
