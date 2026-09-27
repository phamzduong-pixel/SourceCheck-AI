import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ResearchChatPage } from '../pages/ResearchChatPage';
import { AIPreferencesProvider } from '../context/AIPreferencesContext';
import { AuthProvider } from '../context/AuthContext';
import { documentService } from '../services/documents';
import { qaService } from '../services/qa';
import conversationService from '../services/conversations';

const answer = {
  question: 'Noi dung tai lieu la gi?',
  answer: 'Noi dung da duoc kiem chung.',
  status: 'SUPPORTED' as const,
  claims: [], evidence: [], citations: [], evidence_coverage: 1,
  verification_summary: { SUPPORTED: 0, PARTIALLY_SUPPORTED: 0, REFUTED: 0, NOT_ENOUGH_INFO: 0 },
  metadata: {},
};

const renderChat = () => render(
  <MemoryRouter initialEntries={['/']}>
    <AuthProvider><AIPreferencesProvider><Routes>
      <Route path="/" element={<ResearchChatPage />} />
      <Route path="/chat/:conversationId" element={<ResearchChatPage />} />
    </Routes></AIPreferencesProvider></AuthProvider>
  </MemoryRouter>
);

describe('Research Chat document-scoped request (Checkpoint F1)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.spyOn(conversationService, 'createConversation').mockResolvedValue({
      id: 'conv-f1', title: 'Research', is_pinned: false,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    });
    vi.spyOn(conversationService, 'listMessages').mockResolvedValue([]);
  });

  it('sends the uploaded document id with a Q&A request', async () => {
    vi.spyOn(documentService, 'uploadDocument').mockResolvedValue({
      document_id: 'doc-f1', title: 'scope.txt', doc_type: 'txt', page_count: 1,
      total_chunks: 1, metadata: {}, chunks: [],
    });
    const ask = vi.spyOn(qaService, 'askQuestion').mockResolvedValue(answer);
    renderChat();

    fireEvent.change(screen.getByTestId('research-file-input'), {
      target: { files: [new File(['evidence'], 'scope.txt', { type: 'text/plain' })] },
    });
    await screen.findByTestId('file-chip-scope.txt');
    fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Noi dung tai lieu la gi?' } });
    fireEvent.click(screen.getByTestId('btn-ask'));

    await waitFor(() => expect(ask).toHaveBeenCalledWith(expect.objectContaining({
      question: 'Noi dung tai lieu la gi?', document_ids: ['doc-f1'], search_enabled: true,
    })));
  });
});