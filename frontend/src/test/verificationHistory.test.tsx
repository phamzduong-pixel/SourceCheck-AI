import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { VerificationHistoryPage } from '../pages/VerificationHistoryPage';
import { verificationService } from '../services/verification';

const historyItem = {
  request_id: 'history-request-1',
  question: 'Tăng trưởng GDP Việt Nam năm 2023 đạt bao nhiêu?',
  answer_preview: 'Tăng trưởng GDP Việt Nam năm 2023 đạt 5.05%.',
  overall_verdict: 'SUPPORTED',
  status: 'COMPLETED',
  evidence_coverage: 1,
  created_at: '2025-01-15T10:30:00Z',
};

const report = {
  request_id: historyItem.request_id,
  status: 'COMPLETED',
  overall_verdict: 'SUPPORTED',
  summary: 'Kết quả có căn cứ từ tài liệu.',
  claims_count: 1,
  created_at: historyItem.created_at,
  claims: [{
    claim_id: 'claim-1',
    claim_text: 'Tăng trưởng GDP Việt Nam năm 2023 đạt 5.05%.',
    verdict: 'SUPPORTED',
    confidence_score: 0.95,
    explanation: 'Khớp với nguồn tài liệu.',
    evidences: [{
      evidence_id: 'evidence-1',
      source_title: 'Báo cáo Kinh tế - Xã hội 2023',
      source_url: 'https://gso.gov.vn/gdp-2023',
      snippet: 'Tăng trưởng GDP năm 2023 đạt 5.05%.',
      quote: 'Tăng trưởng GDP năm 2023 đạt 5.05%.',
      stance: 'SUPPORTS',
      relevance_score: 0.95,
    }],
  }],
};

const renderPage = () => render(
  <MemoryRouter>
    <VerificationHistoryPage />
  </MemoryRouter>
);

describe('VerificationHistoryPage', () => {
  afterEach(() => vi.restoreAllMocks());

  it('renders persisted history and opens its real report on demand', async () => {
    vi.spyOn(verificationService, 'getHistory').mockResolvedValueOnce({ items: [historyItem], skip: 0, limit: 20 });
    const reportSpy = vi.spyOn(verificationService, 'getVerificationReport').mockResolvedValueOnce(report);

    renderPage();

    expect(screen.getByText('Đang tải lịch sử kiểm chứng...')).toBeInTheDocument();
    expect(await screen.findByText(historyItem.question)).toBeInTheDocument();
    expect(screen.getByText('Evidence Coverage: 100%')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Xem kết quả' }));

    await waitFor(() => expect(reportSpy).toHaveBeenCalledWith(historyItem.request_id));
    expect(await screen.findByTestId('verification-result-card')).toBeInTheDocument();
    expect(screen.getByText('Báo cáo Kinh tế - Xã hội 2023')).toBeInTheDocument();
  });

  it('renders an empty state without a crash', async () => {
    vi.spyOn(verificationService, 'getHistory').mockResolvedValueOnce({ items: [], skip: 0, limit: 20 });

    renderPage();

    expect(await screen.findByTestId('verification-history-empty')).toBeInTheDocument();
  });

  it('renders a recoverable history loading error', async () => {
    vi.spyOn(verificationService, 'getHistory').mockRejectedValueOnce(new Error('Không thể kết nối'));

    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể tải lịch sử kiểm chứng.');
    expect(screen.getByRole('button', { name: 'Thử lại' })).toBeInTheDocument();
  });
});
