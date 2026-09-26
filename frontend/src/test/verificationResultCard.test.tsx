import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VerificationResultCard } from '../components/qa/VerificationResultCard';
import { VerificationResultResponse } from '../types/verification';

const report: VerificationResultResponse = {
  request_id: 'report-1',
  status: 'COMPLETED',
  overall_verdict: 'MIXED',
  claims_count: 4,
  created_at: '2026-09-26T00:00:00Z',
  claims: [
    { claim_text: 'Supported claim', verdict: 'SUPPORTED', confidence_score: 0.9, evidences: [{ source_title: 'Document A', snippet: 'Supporting excerpt', quote: 'Exact supporting quote', stance: 'SUPPORTS', relevance_score: 0.9, source_url: 'https://example.com/a' }] },
    { claim_text: 'Partially supported claim', verdict: 'PARTIALLY_SUPPORTED', confidence_score: 0.7, evidences: [] },
    { claim_text: 'Refuted claim', verdict: 'REFUTED', confidence_score: 0.8, evidences: [] },
    { claim_text: 'Unresolved claim', verdict: 'NOT_ENOUGH_INFO', confidence_score: 0.2, evidences: [] },
  ],
};

describe('VerificationResultCard', () => {
  it('renders real report claims, all verdicts, source link, and exact quote', () => {
    render(<VerificationResultCard report={report} />);

    expect(screen.getByTestId('verification-result-card')).toBeInTheDocument();
    expect(screen.getByText('SUPPORTED')).toBeInTheDocument();
    expect(screen.getByText('PARTIALLY_SUPPORTED')).toBeInTheDocument();
    expect(screen.getByText('REFUTED')).toBeInTheDocument();
    expect(screen.getByText('NOT_ENOUGH_INFO')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Document A' })).toHaveAttribute('href', 'https://example.com/a');
    expect(screen.getByText('Exact supporting quote')).toBeInTheDocument();
  });
});