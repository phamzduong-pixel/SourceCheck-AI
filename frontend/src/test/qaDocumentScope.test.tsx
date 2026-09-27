import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QAPage } from '../pages/QAPage';
import { qaService } from '../services/qa';
import { documentService } from '../services/documents';

vi.mock('../hooks/useAIPreferences', () => ({
  useAIPreferences: () => ({
    t: (key: string) => key,
    showSources: true,
    showVerification: true,
  }),
}));

const availableDocuments = [
  { id: 'doc-a', title: 'Document A', doc_type: 'txt', created_at: '2026-01-01', chunk_count: 1 },
  { id: 'doc-b', title: 'Document B', doc_type: 'pdf', created_at: '2026-01-02', chunk_count: 2 },
  { id: 'doc-c', title: 'Document C', doc_type: 'docx', created_at: '2026-01-03', chunk_count: 3 },
];

const answer = {
  question: 'Test question',
  answer: 'Answer',
  status: 'SUPPORTED',
  claims: [],
  evidence: [],
  citations: [],
  evidence_coverage: 1,
  verification_summary: {},
  metadata: {},
};

const renderPage = () => render(<MemoryRouter><QAPage /></MemoryRouter>);

describe('Q&A document scope (Checkpoint C)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(documentService, 'listDocuments').mockResolvedValue({
      items: availableDocuments,
      total: availableDocuments.length,
      page: 1,
      page_size: 100,
      total_pages: 1,
    });
  });

  it('allows selecting one document and shows the active scope', async () => {
    renderPage();

    const checkbox = await screen.findByTestId('document-checkbox-doc-a');
    fireEvent.click(checkbox);

    expect(checkbox).toBeChecked();
    expect(screen.getByTestId('active-document-scope')).toHaveTextContent('Document A');
  });

  it('allows selecting multiple documents and shows only the selected scope', async () => {
    renderPage();

    fireEvent.click(await screen.findByTestId('document-checkbox-doc-a'));
    fireEvent.click(screen.getByTestId('document-checkbox-doc-c'));

    expect(screen.getByTestId('document-checkbox-doc-a')).toBeChecked();
    expect(screen.getByTestId('document-checkbox-doc-c')).toBeChecked();
    expect(screen.getByTestId('active-document-scope')).toHaveTextContent('Document A, Document C');
    expect(screen.getByTestId('active-document-scope')).not.toHaveTextContent('Document B');
  });

  it('sends the exact selected document_ids with the Q&A request', async () => {
    const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValue(answer);
    renderPage();

    fireEvent.click(await screen.findByTestId('document-checkbox-doc-a'));
    fireEvent.click(screen.getByTestId('document-checkbox-doc-b'));
    fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Scoped question' } });
    fireEvent.click(screen.getByTestId('btn-ask'));

    await waitFor(() => expect(askSpy).toHaveBeenCalledTimes(1));
    expect(askSpy).toHaveBeenCalledWith({
      question: 'Scoped question',
      top_k: 5,
      search_mode: 'hybrid',
      document_ids: ['doc-a', 'doc-b'],
    });
  });

  it('omits document_ids when no document is selected for backward compatibility', async () => {
    const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValue(answer);
    renderPage();

    fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Unscoped question' } });
    fireEvent.click(screen.getByTestId('btn-ask'));

    await waitFor(() => expect(askSpy).toHaveBeenCalledTimes(1));
    expect(askSpy).toHaveBeenCalledWith({
      question: 'Unscoped question',
      top_k: 5,
      search_mode: 'hybrid',
    });
    expect(askSpy.mock.calls[0][0]).not.toHaveProperty('document_ids');
  });
});