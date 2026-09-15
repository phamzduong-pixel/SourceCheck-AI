// frontend/src/services/conversations.ts

/**
 * Service layer for Conversation History backend API.
 * Provides TypeScript types mirroring backend schemas and thin wrappers
 * around the existing `apiClient`.
 */

import { apiClient } from './apiClient';

// Types – match backend `app/schemas/conversation.py`
export interface Conversation {
  id: string; // UUID string
  title: string;
  is_pinned: boolean;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

export interface Message {
  id: string;
  role: string; // e.g. "user", "assistant", "system"
  content: string;
  extra_metadata?: Record<string, any>;
  created_at: string;
}

/** List all conversations belonging to the current authenticated user. */
export const listConversations = async (): Promise<Conversation[]> => {
  // Match the backend route exactly and avoid an auth-sensitive redirect.
  return apiClient.get<Conversation[]>('/conversations/');
};

/** Create a new conversation for the current user. */
export const createConversation = async (title?: string): Promise<Conversation> => {
  // POST /api/v1/conversations with optional title payload
  const payload = title ? { title } : {};
  return apiClient.post<Conversation>('/conversations', payload);
};

/** Retrieve a single conversation by its UUID. */
export const getConversation = async (id: string): Promise<Conversation> => {
  return apiClient.get<Conversation>(`/conversations/${id}`);
};

/** List all messages belonging to a conversation. */
export const listMessages = async (conversationId: string): Promise<Message[]> => {
  return apiClient.get<Message[]>(`/conversations/${conversationId}/messages`);
};

/** Update a conversation's mutable fields (title, is_pinned). */
export const updateConversation = async (
  id: string,
  payload: Partial<{ title: string; is_pinned: boolean }>
): Promise<Conversation> => {
  return apiClient.patch<Conversation>(`/conversations/${id}`, payload);
};

/** Delete a conversation by its UUID. */
export const deleteConversation = async (id: string): Promise<void> => {
  return apiClient.delete(`/conversations/${id}`);
};

export const conversationService = {
  listConversations,
  createConversation,
  getConversation,
  listMessages,
  updateConversation,
  deleteConversation,
};

export default conversationService;
