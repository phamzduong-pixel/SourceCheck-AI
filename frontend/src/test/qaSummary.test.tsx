import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QAPage } from '../pages/QAPage';
import { qaService } from '../services/qa';
import { documentService } from '../services/documents';
import { FinalAnswerResponse } from '../types/qa';

vi.mock('../hooks/useAIPreferences', () => ({
  useAIPreferences: () => ({
    t: (key: string) => key,
    showSources: true,
    showVerification: true,
  }),
}));

const documents = [
  { id: 'doc-a', title: 'Document A', doc_type: 'txt', created_at: '2026-01-01', chunk_count: 2 },
  { id: 'doc-b', title: 'Document B', doc_type: 'pdf', created_at: '2026-01-02', chunk_count: 3 },
];

const summaryResponse: FinalAnswerResponse = {
  question: 'Summarize Document B',
  answer: 'Document B reports a grounded finding.',
  status: 'PARTIALLY_SUPPORTED',
  claims: [],
  evidence: [],
  citations: [],
  evidence_coverage: 1,
  verification_summary: { SUPPORTED: 1, PARTIALLY_SUPPORTED: 0, REFUTED: 0, NOT_ENOUGH_INFO: 0 },
  metadata: {
    task_type: 'summary',
    document_chunks_total: 3,
    document_chunks_processed: 2,
    document_coverage: 0.6667,
    summary_claim_coverage: 1,
    summary_batch_count: 2,
    summary_successful_batch_count: 1,
  },
};

const insufficientSummaryResponse: FinalAnswerResponse = {
  ...summaryResponse,
  status: 'INSUFFICIENT_EVIDENCE',
  answer: 'The selected document does not contain enough evidence.',
  metadata: {
    ...summaryResponse.metadata,
    document_chunks_processed: 0,
    document_coverage: 0,
    summary_claim_coverage: 0,
  },
};

const renderPage = () => render(<MemoryRouter><QAPage /></MemoryRouter>);

describe('Document-grounded summary UI (Checkpoint E3)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(documentService, 'listDocuments').mockResolvedValue({
      items: documents,
      total: documents.length,
      page: 1,
      page_size: 100,
      total_pages: 1,
    });
  });

  it('requires one document for summary and sends task_type with exactly that document', async () => {
    const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValue(summaryResponse);
    renderPage();

    fireEvent.click(screen.getByTestId('operation-summary'));
    expect(screen.getByTestId('summary-operation-hint')).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('question-textarea'), {
      target: { value: 'Summarize the selected paper' },
    });
    expect(screen.getByTestId('btn-ask')).toBeDisabled();

    const documentA = await screen.findByTestId('document-checkbox-doc-a');
    const documentB = screen.getByTestId('document-checkbox-doc-b');
    fireEvent.click(documentA);
    fireEvent.click(documentB);

    expect(documentA).not.toBeChecked();
    expect(documentB).toBeChecked();
    expect(screen.getByTestId('active-document-scope')).toHaveTextContent('Summarizing: Document B');

    fireEvent.click(screen.getByTestId('btn-ask'));

    await waitFor(() => expect(askSpy).toHaveBeenCalledTimes(1));
    expect(askSpy).toHaveBeenCalledWith({
      question: 'Summarize the selected paper',
      top_k: 5,
      search_mode: 'hybrid',
      task_type: 'summary',
      document_ids: ['doc-b'],
    });
  });

  it('shows selected document, coverage, and partial-batch status for a summary result', async () => {
    vi.spyOn(qaService, 'askQuestion').mockResolvedValue(summaryResponse);
    renderPage();

    fireEvent.click(screen.getByTestId('operation-summary'));
    fireEvent.click(await screen.findByTestId('document-checkbox-doc-b'));
    fireEvent.change(screen.getByTestId('question-textarea'), {
      target: { value: 'Summarize Document B' },
    });
    fireEvent.click(screen.getByTestId('btn-ask'));

    expect(await screen.findByTestId('summary-grounding-metadata')).toBeInTheDocument();
    expect(screen.getByTestId('summary-document-title')).toHaveTextContent('Document B');
    expect(screen.getByTestId('summary-chunks-processed')).toHaveTextContent('2/3');
    expect(screen.getByTestId('summary-document-coverage')).toHaveTextContent('67%');
    expect(screen.getByTestId('summary-claim-coverage')).toHaveTextContent('100%');
    expect(screen.getByTestId('summary-grounding-status')).toHaveTextContent(/Partial summary/i);
  });

  it('renders insufficient evidence state for an ungrounded summary', async () => {
    vi.spyOn(qaService, 'askQuestion').mockResolvedValue(insufficientSummaryResponse);
    renderPage();

    fireEvent.click(screen.getByTestId('operation-summary'));
    fireEvent.click(await screen.findByTestId('document-checkbox-doc-a'));
    fireEvent.change(screen.getByTestId('question-textarea'), {
      target: { value: 'Summarize Document A' },
    });
    fireEvent.click(screen.getByTestId('btn-ask'));

    expect(await screen.findByTestId('summary-grounding-status')).toHaveTextContent(/Insufficient evidence/i);
    expect(screen.getByTestId('answer-status-pill')).toHaveTextContent('INSUFFICIENT_EVIDENCE');
  });

  it('keeps the existing unscoped Q&A request contract', async () => {
    const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValue({
      ...summaryResponse,
      metadata: {},
      status: 'SUPPORTED',
    });
    renderPage();

    fireEvent.change(screen.getByTestId('question-textarea'), {
      target: { value: 'Existing Q&A question' },
    });
    fireEvent.click(screen.getByTestId('btn-ask'));

    await waitFor(() => expect(askSpy).toHaveBeenCalledTimes(1));
    expect(askSpy).toHaveBeenCalledWith({
      question: 'Existing Q&A question',
      top_k: 5,
      search_mode: 'hybrid',
    });
  });
});