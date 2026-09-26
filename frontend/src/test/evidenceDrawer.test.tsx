import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EvidenceDrawer } from '../components/qa/EvidenceDrawer';

const citation = {
  citation_id: 'citation-1',
  claim_id: 'claim-1',
  evidence_id: 'evidence-1',
  source_name: 'Document A',
  source_url: 'https://example.com/document-a',
  quote: 'Exact quote returned by the API.',
  stance: 'SUPPORTS',
  footnote_index: 1,
  relevance_score: 0.92,
};

const evidence = {
  evidence_id: 'evidence-1',
  chunk_id: 'chunk-1',
  content: 'Full passage returned by the API.',
  score: 0.92,
  source_title: 'Document A',
  source_url: 'https://example.com/document-a',
  page_number: 7,
};

describe('EvidenceDrawer citation to evidence interaction', () => {
  it('renders API source, exact quote, URL, page, stance, and claim mapping', () => {
    render(<EvidenceDrawer isOpen onClose={vi.fn()} citation={citation} evidence={evidence} />);

    expect(screen.getByText('Document A')).toBeInTheDocument();
    expect(screen.getByTestId('evidence-quote')).toHaveTextContent('Exact quote returned by the API.');
    expect(screen.getByTestId('evidence-full-content')).toHaveTextContent('Full passage returned by the API.');
    expect(screen.getByTestId('evidence-source-url')).toHaveAttribute('href', 'https://example.com/document-a');
    expect(screen.getByText('Trang 7')).toBeInTheDocument();
    expect(screen.getByTestId('evidence-stance-badge')).toHaveTextContent('SUPPORTS');
    expect(screen.getByText('claim-1')).toBeInTheDocument();
  });

  it('does not invent optional metadata when API fields are missing', () => {
    render(
      <EvidenceDrawer
        isOpen
        onClose={vi.fn()}
        citation={{ ...citation, source_url: null, quote: '', stance: '' }}
        evidence={{ ...evidence, source_url: null, page_number: null, content: '' }}
      />,
    );

    expect(screen.queryByTestId('evidence-source-url')).not.toBeInTheDocument();
    expect(screen.queryByTestId('evidence-quote')).not.toBeInTheDocument();
    expect(screen.queryByText('Trang 7')).not.toBeInTheDocument();
    expect(screen.getByTestId('drawer-no-evidence')).toBeInTheDocument();
  });
});