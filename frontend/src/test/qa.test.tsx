/**
 * Test Suite for Grounded Q&A Chat (FE-03).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QAPage } from '../pages/QAPage';
import { qaService } from '../services/qa';
import { ApiClientError } from '../services/apiClient';
import { FinalAnswerResponse } from '../types/qa';

const mockFinalAnswer: FinalAnswerResponse = {
  question: 'Việt Nam gia nhập WTO năm nào?',
  answer: 'Việt Nam chính thức trở thành thành viên thứ 150 của WTO vào ngày 11 tháng 1 năm 2007 [1]. Quá trình đàm phán kéo dài 11 năm [2].',
  status: 'SUPPORTED',
  claims: [
    {
      claim_id: 'claim-1',
      text: 'Việt Nam chính thức trở thành thành viên thứ 150 của WTO vào năm 2007',
      order: 1,
      context_sentence: 'Việt Nam chính thức trở thành thành viên thứ 150 của WTO vào ngày 11 tháng 1 năm 2007.',
      verifiable: true,
    },
    {
      claim_id: 'claim-2',
      text: 'Quá trình đàm phán gia nhập WTO của Việt Nam kéo dài 11 năm',
      order: 2,
      context_sentence: 'Quá trình đàm phán kéo dài 11 năm.',
      verifiable: true,
    },
  ],
  evidence: [
    {
      evidence_id: 'E1',
      chunk_id: 'chunk-101',
      content: 'Ngày 11-1-2007, Việt Nam chính thức trở thành thành viên đầy đủ thứ 150 của Tổ chức Thương mại Thế giới.',
      score: 0.98,
      source_title: 'Cổng thông tin điện tử Bộ Công Thương',
      source_url: 'https://moit.gov.vn/wto-2007',
      publisher: 'Bộ Công Thương',
      page_number: 1,
    },
    {
      evidence_id: 'E2',
      chunk_id: 'chunk-102',
      content: 'Sau 11 năm đàm phán kiên trì kể từ khi nộp đơn năm 1995, Việt Nam đã hoàn tất tiến trình gia nhập.',
      score: 0.91,
      source_title: 'Báo Chính phủ',
      source_url: 'https://baochinhphu.vn/wto-11-nam',
      publisher: 'Báo Chính phủ',
      page_number: 3,
    },
  ],
  citations: [
    {
      citation_id: 'cit-1',
      claim_id: 'claim-1',
      evidence_id: 'E1',
      source_name: 'Bộ Công Thương',
      source_url: 'https://moit.gov.vn/wto-2007',
      quote: 'Ngày 11-1-2007, Việt Nam chính thức trở thành thành viên đầy đủ thứ 150 của Tổ chức Thương mại Thế giới.',
      stance: 'SUPPORTS',
      footnote_index: 1,
      relevance_score: 0.98,
    },
    {
      citation_id: 'cit-2',
      claim_id: 'claim-2',
      evidence_id: 'E2',
      source_name: 'Báo Chính phủ',
      source_url: 'https://baochinhphu.vn/wto-11-nam',
      quote: 'Sau 11 năm đàm phán kiên trì kể từ khi nộp đơn năm 1995...',
      stance: 'SUPPORTS',
      footnote_index: 2,
      relevance_score: 0.91,
    },
  ],
  evidence_coverage: 1.0,
  verification_summary: {
    SUPPORTED: 2,
    PARTIALLY_SUPPORTED: 0,
    REFUTED: 0,
    NOT_ENOUGH_INFO: 0,
  },
  metadata: {
    retriever: 'hybrid_rrf',
  },
};

describe('Grounded Q&A Core Feature (FE-03)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('1. Render & Empty State', () => {
    it('renders Q&A page header, composer textarea, and empty state initially', () => {
      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      // Verify Page Header
      expect(screen.getByText(/hỏi đáp có dẫn nguồn|grounded q&a/i)).toBeInTheDocument();

      // Verify Composer
      expect(screen.getByTestId('question-textarea')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /ask question/i })).toBeInTheDocument();

      // Verify Empty State is shown
      expect(screen.getByTestId('qa-empty-state')).toBeInTheDocument();
      expect(screen.getByText('Khám phá tri thức có đối soát')).toBeInTheDocument();
    });

    it('disables Ask button when input is empty and enables when user types', () => {
      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      const textarea = screen.getByTestId('question-textarea') as HTMLTextAreaElement;
      const askBtn = screen.getByTestId('btn-ask') as HTMLButtonElement;

      // Empty input -> disabled
      expect(askBtn).toBeDisabled();

      // Type whitespace only -> still disabled
      fireEvent.change(textarea, { target: { value: '   ' } });
      expect(askBtn).toBeDisabled();

      // Type actual question -> enabled
      fireEvent.change(textarea, { target: { value: 'Việt Nam gia nhập WTO khi nào?' } });
      expect(askBtn).not.toBeDisabled();
    });
  });

  describe('2. Submitting Question & API Dispatch', () => {
    it('dispatches askQuestion with accurate payload on submit', async () => {
      const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      const textarea = screen.getByTestId('question-textarea');
      const askBtn = screen.getByTestId('btn-ask');

      fireEvent.change(textarea, { target: { value: 'Việt Nam gia nhập WTO năm nào?' } });
      fireEvent.click(askBtn);

      expect(askSpy).toHaveBeenCalledTimes(1);
      expect(askSpy).toHaveBeenCalledWith({
        question: 'Việt Nam gia nhập WTO năm nào?',
        top_k: 5,
        search_mode: 'hybrid',
      });

      await waitFor(() => {
        expect(screen.getByTestId('qa-answer-container')).toBeInTheDocument();
      });
    });

    it('triggers question submission via Ctrl+Enter shortcut', async () => {
      const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      const textarea = screen.getByTestId('question-textarea');
      fireEvent.change(textarea, { target: { value: 'Phím tắt Ctrl+Enter?' } });
      fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });

      expect(askSpy).toHaveBeenCalledTimes(1);

      await waitFor(() => {
        expect(screen.getByTestId('qa-answer-container')).toBeInTheDocument();
      });
    });

    it('displays loading indicator and disables submit while request is pending', async () => {
      // Create a deferred promise to control resolution
      let resolvePromise: (val: any) => void;
      const deferredPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      vi.spyOn(qaService, 'askQuestion').mockImplementationOnce(() => deferredPromise as any);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      const textarea = screen.getByTestId('question-textarea');
      const askBtn = screen.getByTestId('btn-ask');

      fireEvent.change(textarea, { target: { value: 'Đang tải...' } });
      fireEvent.click(askBtn);

      // Verify Loading State
      expect(screen.getByTestId('qa-loading-state')).toBeInTheDocument();
      expect(askBtn).toBeDisabled();

      // Resolve API
      resolvePromise!(mockFinalAnswer);

      // Verify Loading State dismissed
      await waitFor(() => {
        expect(screen.queryByTestId('qa-loading-state')).not.toBeInTheDocument();
        expect(screen.getByTestId('qa-answer-container')).toBeInTheDocument();
      });
    });
  });

  describe('3. Successful Answer, Citations & Provenance Render', () => {
    it('renders synthesized answer, clickable citations [1] and [2]', async () => {
      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Test question' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('qa-answer-container')).toBeInTheDocument();
        const answerEl = screen.getByTestId('answer-rendered-text');
        expect(within(answerEl).getByText(/Việt Nam chính thức trở thành thành viên thứ 150/i)).toBeInTheDocument();
      });

      // Verify Citations rendered as interactive buttons
      const cit1 = screen.getByTestId('citation-btn-1');
      const cit2 = screen.getByTestId('citation-btn-2');
      expect(cit1).toBeInTheDocument();
      expect(cit1).toHaveTextContent('[1]');
      expect(cit2).toBeInTheDocument();
      expect(cit2).toHaveTextContent('[2]');

      // Verify Status Pill
      expect(screen.getByTestId('answer-status-pill')).toHaveTextContent('SUPPORTED');
    });

    it('clicking citation [1] opens Evidence Drawer with exact provenance details', async () => {
      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Test citation click' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('citation-btn-1')).toBeInTheDocument();
      });

      // Click Citation [1]
      fireEvent.click(screen.getByTestId('citation-btn-1'));

      // Verify Evidence Drawer is open
      const drawer = screen.getByTestId('evidence-drawer');
      expect(drawer).toBeInTheDocument();

      // Verify Source Name & URL
      expect(within(drawer).getByText('Bộ Công Thương')).toBeInTheDocument();
      expect(within(drawer).getByTestId('evidence-source-url')).toHaveAttribute(
        'href',
        'https://moit.gov.vn/wto-2007'
      );

      // Verify Quote & Stance
      expect(within(drawer).getByTestId('evidence-stance-badge')).toHaveTextContent('SUPPORTS');
      expect(within(drawer).getByTestId('evidence-quote')).toHaveTextContent(
        'Ngày 11-1-2007, Việt Nam chính thức trở thành thành viên đầy đủ thứ 150'
      );

      // Verify Full Passage from Chunk
      expect(within(drawer).getByTestId('evidence-full-content')).toBeInTheDocument();

      // Click Close button
      fireEvent.click(screen.getByTestId('drawer-close-btn'));
      expect(screen.queryByTestId('evidence-drawer')).not.toBeInTheDocument();
    });

    it('handles citation without matching evidence gracefully without crashing', async () => {
      const answerWithoutEvidence: FinalAnswerResponse = {
        question: 'Câu hỏi không có bằng chứng chi tiết?',
        answer: 'Nhận định này cần kiểm tra thêm [1].',
        status: 'INSUFFICIENT_EVIDENCE',
        claims: [],
        evidence: [], // No evidence items returned from backend
        citations: [
          {
            citation_id: 'cit-sparse',
            claim_id: 'claim-x',
            evidence_id: 'E-nonexistent',
            source_name: 'Nguồn chưa xác định',
            quote: '', // Empty quote
            stance: 'CONTEXT',
            footnote_index: 1,
            relevance_score: 0,
          },
        ],
        evidence_coverage: 0.0,
        verification_summary: { SUPPORTED: 0, PARTIALLY_SUPPORTED: 0, REFUTED: 0, NOT_ENOUGH_INFO: 1 },
        metadata: {},
      };

      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(answerWithoutEvidence);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Câu hỏi thiếu evidence' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('citation-btn-1')).toBeInTheDocument();
      });

      // Click citation
      fireEvent.click(screen.getByTestId('citation-btn-1'));

      const drawer = screen.getByTestId('evidence-drawer');
      expect(drawer).toBeInTheDocument();

      // Verify graceful fallback: no crash, shows empty evidence state
      expect(within(drawer).getByTestId('drawer-no-evidence')).toBeInTheDocument();
      expect(within(drawer).getByTestId('evidence-source-title')).toHaveTextContent('Nguồn chưa xác định');

      // Close via Escape key
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(screen.queryByTestId('evidence-drawer')).not.toBeInTheDocument();
    });

    it('closes Evidence Drawer when backdrop is clicked', async () => {
      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Test backdrop' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('citation-btn-1')).toBeInTheDocument();
      });

      // Open drawer
      fireEvent.click(screen.getByTestId('citation-btn-1'));
      expect(screen.getByTestId('evidence-drawer')).toBeInTheDocument();

      // Click backdrop
      fireEvent.click(screen.getByTestId('evidence-drawer-backdrop'));
      expect(screen.queryByTestId('evidence-drawer')).not.toBeInTheDocument();
    });

    it('renders Evidence Coverage bar and Verification Summary correctly', async () => {
      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Test coverage' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('evidence-coverage-card')).toBeInTheDocument();
        expect(screen.getByTestId('coverage-percentage-value')).toHaveTextContent('100%');
        expect(screen.getByTestId('coverage-bar-fill')).toHaveStyle('width: 100%');
        expect(screen.getByText('Supported: 2')).toBeInTheDocument();
      });
    });

    it('renders atomic claims list with sequence numbers', async () => {
      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Test claims' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('claims-section')).toBeInTheDocument();
        expect(screen.getByText('2 claims')).toBeInTheDocument();
        expect(screen.getByTestId('claim-item-claim-1')).toHaveTextContent('#1');
        expect(screen.getByTestId('claim-item-claim-2')).toHaveTextContent('#2');
      });
    });
  });

  describe('4. Error & Edge Case Handling', () => {
    it('displays validation error alert on HTTP 422 without clearing user input', async () => {
      vi.spyOn(qaService, 'askQuestion').mockRejectedValueOnce(
        new ApiClientError('Dữ liệu câu hỏi quá ngắn.', 422)
      );

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      const textarea = screen.getByTestId('question-textarea');
      fireEvent.change(textarea, { target: { value: 'a' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('qa-error-alert')).toBeInTheDocument();
        expect(screen.getByText('Dữ liệu câu hỏi quá ngắn.')).toBeInTheDocument();
        // User input is preserved
        expect(textarea).toHaveValue('a');
      });
    });

    it('displays friendly error message on HTTP 500 server exception', async () => {
      vi.spyOn(qaService, 'askQuestion').mockRejectedValueOnce(
        new ApiClientError('Internal error', 500)
      );

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Error trigger' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('qa-error-alert')).toBeInTheDocument();
        expect(screen.getByText(/máy chủ đang gặp sự cố/i)).toBeInTheDocument();
      });
    });

    it('displays network failure message when connection is broken (statusCode 0)', async () => {
      vi.spyOn(qaService, 'askQuestion').mockRejectedValueOnce(
        new ApiClientError('Network fail', 0)
      );

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Network test' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('qa-error-alert')).toBeInTheDocument();
        expect(screen.getByText(/không thể kết nối đến máy chủ/i)).toBeInTheDocument();
      });
    });

    it('clicking sample question in empty state populates and submits question', async () => {
      const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      const sampleBtn = screen.getByTestId('sample-question-0');
      fireEvent.click(sampleBtn);

      expect(askSpy).toHaveBeenCalledTimes(1);
      expect(askSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          question: expect.stringContaining('WTO'),
        })
      );

      await waitFor(() => {
        expect(screen.getByTestId('qa-answer-container')).toBeInTheDocument();
      });
    });
  });

  describe('5. Claims Breakdown & Evidence Coverage (FE-03.3)', () => {
    it('renders claims with backend verdicts, confidence, explanation, and unverifiable flags', async () => {
      const answerWithRichClaims: FinalAnswerResponse = {
        question: 'Câu hỏi kiểm chứng chuyên sâu',
        answer: 'Tuyên bố thứ nhất đã kiểm chứng [1]. Tuyên bố thứ hai bác bỏ [2]. Tuyên bố thứ ba là ý kiến [3].',
        status: 'PARTIALLY_SUPPORTED',
        claims: [
          {
            claim_id: 'claim-supported',
            text: 'Tuyên bố thứ nhất là sự thật khách quan',
            order: 1,
            context_sentence: 'Tuyên bố thứ nhất đã kiểm chứng.',
            verifiable: true,
            verdict: 'SUPPORTED',
            confidence: 0.95,
            explanation: 'Bằng chứng E1 khẳng định số liệu hoàn toàn chính xác.',
          },
          {
            claim_id: 'claim-refuted',
            text: 'Tuyên bố thứ hai là thông tin sai lệch',
            order: 2,
            context_sentence: 'Tuyên bố thứ hai bác bỏ.',
            verifiable: true,
            verdict: 'REFUTED',
            confidence: 0.88,
            explanation: 'Bằng chứng E2 mâu thuẫn trực tiếp với tuyên bố.',
          },
          {
            claim_id: 'claim-unverifiable',
            text: 'Tuyên bố thứ ba là đánh giá chủ quan',
            order: 3,
            context_sentence: 'Tuyên bố thứ ba là ý kiến.',
            verifiable: false,
            explanation: 'Luận điểm mang tính dự báo định tính.',
          },
        ],
        evidence: [
          {
            evidence_id: 'E1',
            chunk_id: 'chunk-1',
            content: 'Nội dung xác thực số 1.',
            score: 0.96,
            source_title: 'Nguồn A',
            source_url: 'https://example.com/a',
          },
          {
            evidence_id: 'E2',
            chunk_id: 'chunk-2',
            content: 'Nội dung bác bỏ số 2.',
            score: 0.92,
            source_title: 'Nguồn B',
            source_url: 'https://example.com/b',
          },
        ],
        citations: [
          {
            citation_id: 'cit-1',
            claim_id: 'claim-supported',
            evidence_id: 'E1',
            source_name: 'Nguồn A',
            source_url: 'https://example.com/a',
            quote: 'Nội dung xác thực số 1.',
            stance: 'SUPPORTS',
            footnote_index: 1,
            relevance_score: 0.96,
          },
          {
            citation_id: 'cit-2',
            claim_id: 'claim-refuted',
            evidence_id: 'E2',
            source_name: 'Nguồn B',
            source_url: 'https://example.com/b',
            quote: 'Nội dung bác bỏ số 2.',
            stance: 'REFUTES',
            footnote_index: 2,
            relevance_score: 0.92,
          },
        ],
        evidence_coverage: 0.67,
        verification_summary: {
          SUPPORTED: 1,
          PARTIALLY_SUPPORTED: 0,
          REFUTED: 1,
          NOT_ENOUGH_INFO: 1,
        },
        metadata: {},
      };

      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(answerWithRichClaims);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Test claims FE-03.3' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('claims-section')).toBeInTheDocument();
      });

      // Claim 1 checks: SUPPORTED, 95%, explanation
      expect(screen.getByTestId('claim-verdict-claim-supported')).toHaveTextContent('SUPPORTED');
      expect(screen.getByTestId('claim-confidence-claim-supported')).toHaveTextContent('95%');
      expect(screen.getByTestId('claim-explanation-claim-supported')).toHaveTextContent('Bằng chứng E1 khẳng định');

      // Claim 2 checks: REFUTED, 88%, explanation
      expect(screen.getByTestId('claim-verdict-claim-refuted')).toHaveTextContent('REFUTED');
      expect(screen.getByTestId('claim-confidence-claim-refuted')).toHaveTextContent('88%');

      // Claim 3 checks: unverifiable badge
      expect(screen.getByTestId('claim-unverifiable-claim-unverifiable')).toHaveTextContent('Không thể kiểm chứng');

      // Coverage card checks
      expect(screen.getByTestId('coverage-percentage-value')).toHaveTextContent('67%');
      expect(screen.getByText('Supported: 1')).toBeInTheDocument();
      expect(screen.getByText('Refuted: 1')).toBeInTheDocument();
    });

    it('links evidence and citations to specific claims and opens Evidence Drawer on citation click', async () => {
      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Test claim citation link' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('claims-section')).toBeInTheDocument();
      });

      // Check linked evidence in Claim 1
      const claim1Citations = screen.getByTestId('claim-evidences-claim-1');
      expect(claim1Citations).toBeInTheDocument();
      expect(screen.getByTestId('claim-evidence-stance-claim-1-1')).toHaveTextContent('SUPPORTS');
      expect(within(claim1Citations).getByText('Bộ Công Thương')).toBeInTheDocument();

      // Click citation [1] button inside the claim card
      const claimCitBtn = screen.getByTestId('claim-citation-btn-claim-1-1');
      expect(claimCitBtn).toHaveTextContent('[1]');
      fireEvent.click(claimCitBtn);

      // Verify Evidence Drawer opens with E1 details
      const drawer = screen.getByTestId('evidence-drawer');
      expect(drawer).toBeInTheDocument();
      expect(within(drawer).getByText('Bộ Công Thương')).toBeInTheDocument();
      expect(within(drawer).getByTestId('evidence-quote')).toHaveTextContent('Ngày 11-1-2007');

      // Close drawer
      fireEvent.click(screen.getByTestId('drawer-close-btn'));
      expect(screen.queryByTestId('evidence-drawer')).not.toBeInTheDocument();
    });

    it('renders claim with no linked evidence gracefully with fallback state', async () => {
      const answerWithOrphanClaim: FinalAnswerResponse = {
        question: 'Claim không có citation',
        answer: 'Câu trả lời không có trích dẫn.',
        status: 'INSUFFICIENT_EVIDENCE',
        claims: [
          {
            claim_id: 'claim-orphan',
            text: 'Một luận điểm không có bằng chứng nào đối chứng.',
            order: 1,
            verifiable: true,
          },
        ],
        evidence: [],
        citations: [],
        evidence_coverage: 0.0,
        verification_summary: { NOT_ENOUGH_INFO: 1 },
        metadata: {},
      };

      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(answerWithOrphanClaim);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Test orphan claim' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('claim-item-claim-orphan')).toBeInTheDocument();
      });

      expect(screen.getByTestId('claim-no-evidence-claim-orphan')).toHaveTextContent('Chưa có bằng chứng liên kết');
      expect(screen.getByTestId('coverage-percentage-value')).toHaveTextContent('0%');
    });

    it('omits Evidence Coverage card when evidence_coverage is null or undefined in response', async () => {
      const answerWithoutCoverage: any = {
        question: 'Không có trường coverage',
        answer: 'Câu trả lời không kèm số liệu coverage.',
        status: 'SUPPORTED',
        claims: [],
        evidence: [],
        citations: [],
        evidence_coverage: undefined, // Backend doesn't provide evidence_coverage
        metadata: {},
      };

      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(answerWithoutCoverage);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Test without coverage' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('qa-answer-container')).toBeInTheDocument();
      });

      // Evidence coverage card should NOT be rendered
      expect(screen.queryByTestId('evidence-coverage-card')).not.toBeInTheDocument();
    });

    it('renders all four verdicts (SUPPORTED, PARTIALLY_SUPPORTED, REFUTED, NOT_ENOUGH_INFO) with verified claim ratio', async () => {
      const fourVerdictsAnswer: FinalAnswerResponse = {
        question: 'Phân tích 4 mức độ kiểm chứng',
        answer: 'Luận điểm 1 đúng [1]. Luận điểm 2 đúng một phần [2]. Luận điểm 3 sai [3]. Luận điểm 4 chưa đủ thông tin [4].',
        status: 'PARTIALLY_SUPPORTED',
        claims: [
          {
            claim_id: 'c-sup',
            text: 'Luận điểm được chứng minh hoàn toàn',
            order: 1,
            verdict: 'SUPPORTED',
            confidence: 0.98,
            verifiable: true,
          },
          {
            claim_id: 'c-part',
            text: 'Luận điểm được chứng minh một phần',
            order: 2,
            verdict: 'PARTIALLY_SUPPORTED',
            confidence: 0.75,
            verifiable: true,
          },
          {
            claim_id: 'c-ref',
            text: 'Luận điểm bị bác bỏ',
            order: 3,
            verdict: 'REFUTED',
            confidence: 0.92,
            verifiable: true,
          },
          {
            claim_id: 'c-nei',
            text: 'Luận điểm chưa đủ thông tin kiểm chứng',
            order: 4,
            verdict: 'NOT_ENOUGH_INFO',
            confidence: 0.40,
            verifiable: true,
          },
        ],
        evidence: [
          {
            evidence_id: 'ev-1',
            chunk_id: 'ch-1',
            content: 'Bằng chứng 1',
            score: 0.98,
            source_title: 'Nguồn 1',
          },
        ],
        citations: [
          {
            citation_id: 'cit-1',
            claim_id: 'c-sup',
            evidence_id: 'ev-1',
            source_name: 'Nguồn 1',
            quote: 'Bằng chứng 1',
            stance: 'SUPPORTS',
            footnote_index: 1,
            relevance_score: 0.98,
          },
        ],
        evidence_coverage: 0.75,
        verification_summary: {
          SUPPORTED: 1,
          PARTIALLY_SUPPORTED: 1,
          REFUTED: 1,
          NOT_ENOUGH_INFO: 1,
        },
        metadata: {},
      };

      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(fourVerdictsAnswer);

      render(
        <MemoryRouter>
          <QAPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('question-textarea'), { target: { value: 'Test 4 verdicts' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('claims-section')).toBeInTheDocument();
      });

      // Verify all 4 verdicts rendered
      expect(screen.getByTestId('claim-verdict-c-sup')).toHaveTextContent('SUPPORTED');
      expect(screen.getByTestId('claim-verdict-c-part')).toHaveTextContent('PARTIALLY_SUPPORTED');
      expect(screen.getByTestId('claim-verdict-c-ref')).toHaveTextContent('REFUTED');
      expect(screen.getByTestId('claim-verdict-c-nei')).toHaveTextContent('NOT_ENOUGH_INFO');

      // Verify Verified Claims Ratio: 3 verified out of 4 total claims
      expect(screen.getByTestId('stat-verified-ratio')).toHaveTextContent('Đối soát: 3/4 claims');

      // Verify Evidence Coverage summary counts
      expect(screen.getByTestId('stat-supported')).toHaveTextContent('Supported: 1');
      expect(screen.getByTestId('stat-partially')).toHaveTextContent('Partially: 1');
      expect(screen.getByTestId('stat-refuted')).toHaveTextContent('Refuted: 1');
      expect(screen.getByTestId('stat-not-enough-info')).toHaveTextContent('Not Enough Info: 1');
    });
  });
});
