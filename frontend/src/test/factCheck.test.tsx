/**
 * Test Suite for Fact-Checking Verification Feature (FE-04.1).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { FactCheckPage } from '../pages/FactCheckPage';
import { verificationService } from '../services/verification';
import { ApiClientError } from '../services/apiClient';
import { VerificationResultResponse, ClaimExtractResponse } from '../types/verification';

const mockClaimExtractResult: ClaimExtractResponse = {
  total_claims: 2,
  claims: [
    {
      claim_id: 'claim_1',
      claim_text: 'Việt Nam chính thức trở thành thành viên WTO năm 2007.',
      context_sentence: 'Việt Nam gia nhập WTO năm 2007 sau 11 năm đàm phán.',
      verifiable: true,
    },
    {
      claim_id: 'claim_2',
      claim_text: 'Quá trình đàm phán gia nhập WTO của Việt Nam kéo dài 11 năm.',
      context_sentence: 'Việt Nam gia nhập WTO năm 2007 sau 11 năm đàm phán.',
      verifiable: true,
    },
  ],
};

const mockVerificationResult: VerificationResultResponse = {
  request_id: 'req-test-uuid-001',
  status: 'COMPLETED',
  overall_verdict: 'TRUE',
  summary: 'Processed 2 claim(s). Verdict: TRUE. All statements are supported by official government documentation.',
  claims_count: 2,
  claims: [
    {
      claim_id: 'claim-001',
      claim_text: 'Việt Nam chính thức trở thành thành viên thứ 150 của WTO vào ngày 11/01/2007.',
      verdict: 'SUPPORTED',
      confidence_score: 0.98,
      explanation: 'Tài liệu từ Bộ Công Thương xác nhận ngày gia nhập và thứ tự thành viên.',
      evidences: [
        {
          evidence_id: 'ev-001',
          source_title: 'Cổng thông tin Bộ Công Thương',
          source_url: 'https://moit.gov.vn/wto-2007',
          publisher: 'Bộ Công Thương',
          snippet: 'Ngày 11-1-2007, Việt Nam chính thức trở thành thành viên thứ 150 của WTO.',
          stance: 'SUPPORTS',
          quote: 'Việt Nam chính thức trở thành thành viên thứ 150 của WTO.',
          relevance_score: 0.95,
        },
      ],
    },
    {
      claim_id: 'claim-002',
      claim_text: 'Đàm phán gia nhập WTO của Việt Nam kéo dài 11 năm.',
      verdict: 'SUPPORTED',
      confidence_score: 0.92,
      explanation: 'Tiến trình đàm phán bắt đầu từ năm 1995 đến cuối năm 2006.',
      evidences: [
        {
          evidence_id: 'ev-002',
          source_title: 'Báo Chính phủ',
          source_url: 'https://baochinhphu.vn/wto-history',
          publisher: 'Báo Chính phủ',
          snippet: 'Sau 11 năm kiên trì đàm phán kể từ 1995, Việt Nam đã hoàn tất tiến trình.',
          stance: 'SUPPORTS',
          quote: 'Sau 11 năm kiên trì đàm phán kể từ 1995...',
          relevance_score: 0.89,
        },
      ],
    },
  ],
  created_at: '2026-09-14T10:00:00Z',
  completed_at: '2026-09-14T10:00:03Z',
};

describe('Fact-Checking Feature (FE-04.1)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('1. Render & Empty State', () => {
    it('renders Fact-Checking header, composer inputs, and empty state initially', () => {
      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      // Verify Header
      expect(screen.getByText(/kiểm chứng thông tin|fact-checking/i)).toBeInTheDocument();
      expect(screen.getByText(/kiểm chứng tính xác thực của nội dung/i)).toBeInTheDocument();

      // Verify Composer
      expect(screen.getByTestId('factcheck-textarea')).toBeInTheDocument();
      expect(screen.getByTestId('factcheck-url-input')).toBeInTheDocument();
      expect(screen.getByTestId('btn-verify')).toBeInTheDocument();

      // Verify Empty State
      expect(screen.getByTestId('verify-empty-state')).toBeInTheDocument();
      expect(screen.getByText('Sẵn sàng đối soát và kiểm chứng tin tức')).toBeInTheDocument();
      expect(screen.getByTestId('sample-claim-0')).toBeInTheDocument();
    });

    it('disables Verify button when text input is empty and enables when valid text is typed', () => {
      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      const textarea = screen.getByTestId('factcheck-textarea');
      const verifyBtn = screen.getByTestId('btn-verify');

      // Empty -> disabled
      expect(verifyBtn).toBeDisabled();

      // Whitespace only -> disabled
      fireEvent.change(textarea, { target: { value: '    ' } });
      expect(verifyBtn).toBeDisabled();

      // Meaningful text -> enabled
      fireEvent.change(textarea, { target: { value: 'Việt Nam gia nhập WTO năm 2007' } });
      expect(verifyBtn).not.toBeDisabled();
    });
  });

  describe('2. Submitting Claim & API Dispatch', () => {
    it('calls verificationService.verifyText with accurate payload on submit', async () => {
      const verifySpy = vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(mockVerificationResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      const textarea = screen.getByTestId('factcheck-textarea');
      const urlInput = screen.getByTestId('factcheck-url-input');
      const verifyBtn = screen.getByTestId('btn-verify');

      fireEvent.change(textarea, { target: { value: 'Việt Nam gia nhập WTO năm 2007.' } });
      fireEvent.change(urlInput, { target: { value: 'https://moit.gov.vn/wto' } });
      fireEvent.click(verifyBtn);

      expect(verifySpy).toHaveBeenCalledTimes(1);
      expect(verifySpy).toHaveBeenCalledWith({
        text: 'Việt Nam gia nhập WTO năm 2007.',
        source_url: 'https://moit.gov.vn/wto',
        enable_contradiction_check: true,
        top_k_evidence: 5,
      });

      await waitFor(() => {
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });
    });

    it('triggers verification submission via Ctrl+Enter shortcut', async () => {
      const verifySpy = vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(mockVerificationResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      const textarea = screen.getByTestId('factcheck-textarea');
      fireEvent.change(textarea, { target: { value: 'Nội dung phím tắt' } });
      fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });

      expect(verifySpy).toHaveBeenCalledTimes(1);

      await waitFor(() => {
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });
    });

    it('displays loading indicator and disables submit while request is pending', async () => {
      let resolvePromise: (val: any) => void;
      const deferredPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      vi.spyOn(verificationService, 'verifyText').mockImplementationOnce(() => deferredPromise as any);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      const textarea = screen.getByTestId('factcheck-textarea');
      const verifyBtn = screen.getByTestId('btn-verify');

      fireEvent.change(textarea, { target: { value: 'Kiểm chứng đang tải...' } });
      fireEvent.click(verifyBtn);

      // Verify Loading State
      expect(screen.getByTestId('verify-loading-state')).toBeInTheDocument();
      expect(screen.getByText(/đang trích xuất nhận định/i)).toBeInTheDocument();
      expect(verifyBtn).toBeDisabled();

      // Resolve API
      resolvePromise!(mockVerificationResult);

      // Verify Loading dismissed and Results displayed
      await waitFor(() => {
        expect(screen.queryByTestId('verify-loading-state')).not.toBeInTheDocument();
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });
    });
  });

  describe('3. Successful Verification Result Rendering', () => {
    it('renders overall verdict, summary, metadata, and verified claims with evidence', async () => {
      vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(mockVerificationResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), { target: { value: 'Test verify' } });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });

      // Verify Overall Verdict Card
      const verdictCard = screen.getByTestId('overall-verdict-card');
      expect(within(verdictCard).getByTestId('overall-verdict-badge')).toHaveTextContent('TRUE');
      expect(within(verdictCard).getByTestId('overall-summary-text')).toHaveTextContent(/All statements are supported/i);
      expect(within(verdictCard).getByTestId('meta-request-id')).toHaveTextContent('req-test-uuid-001');
      expect(within(verdictCard).getByTestId('meta-status')).toHaveTextContent('COMPLETED');
      expect(within(verdictCard).getByTestId('meta-claims-count')).toHaveTextContent('2');

      // Verify Claims List
      expect(screen.getByTestId('claims-count-tag')).toHaveTextContent('2 claims');

      // Claim 1
      const claim1 = screen.getByTestId('verified-claim-claim-001');
      expect(within(claim1).getByTestId('claim-text-claim-001')).toHaveTextContent(
        'Việt Nam chính thức trở thành thành viên thứ 150'
      );
      expect(within(claim1).getByTestId('claim-verdict-claim-001')).toHaveTextContent('SUPPORTED');
      expect(within(claim1).getByTestId('claim-confidence-claim-001')).toHaveTextContent('98%');
      expect(within(claim1).getByTestId('claim-explanation-claim-001')).toHaveTextContent('Bộ Công Thương xác nhận');

      // Evidence in Claim 1
      const ev1 = within(claim1).getByTestId('claim-evidence-claim-001-0');
      expect(within(ev1).getByTestId('evidence-stance-claim-001-0')).toHaveTextContent('SUPPORTS');
      expect(within(ev1).getByText('Cổng thông tin Bộ Công Thương')).toBeInTheDocument();
      expect(within(ev1).getByTestId('evidence-source-url-claim-001-0')).toHaveAttribute(
        'href',
        'https://moit.gov.vn/wto-2007'
      );
      expect(within(ev1).getByText(/Độ khớp: 95%/i)).toBeInTheDocument();

      // Claim 2
      const claim2 = screen.getByTestId('verified-claim-claim-002');
      expect(within(claim2).getByTestId('claim-verdict-claim-002')).toHaveTextContent('SUPPORTED');
      expect(within(claim2).getByTestId('claim-confidence-claim-002')).toHaveTextContent('92%');
    });

    it('renders FALSE and MIXED verdicts correctly from backend', async () => {
      const refutedResult: VerificationResultResponse = {
        request_id: 'req-refuted',
        status: 'COMPLETED',
        overall_verdict: 'FALSE',
        summary: 'Statement is refuted by verified data.',
        claims_count: 1,
        claims: [
          {
            claim_id: 'claim-false',
            claim_text: 'GDP Việt Nam 2023 tăng trưởng 20%.',
            verdict: 'REFUTED',
            confidence_score: 0.95,
            explanation: 'Tổng cục Thống kê xác nhận GDP chỉ đạt 5.05%.',
            evidences: [
              {
                evidence_id: 'ev-refute',
                source_title: 'Tổng cục Thống kê',
                snippet: 'GDP năm 2023 của Việt Nam tăng 5.05%.',
                stance: 'REFUTES',
                relevance_score: 0.94,
              },
            ],
          },
        ],
        created_at: '2026-09-14T10:00:00Z',
      };

      vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(refutedResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), { target: { value: 'GDP 2023 đạt 20%' } });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('overall-verdict-badge')).toHaveTextContent('FALSE');
        expect(screen.getByTestId('claim-verdict-claim-false')).toHaveTextContent('REFUTED');
        expect(screen.getByTestId('evidence-stance-claim-false-0')).toHaveTextContent('REFUTES');
      });
    });
  });

  describe('4. Error Handling & Edge Cases', () => {
    it('displays validation error alert on HTTP 422 without clearing user input', async () => {
      vi.spyOn(verificationService, 'verifyText').mockRejectedValueOnce(
        new ApiClientError('Nội dung quá ngắn.', 422)
      );

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      const textarea = screen.getByTestId('factcheck-textarea');
      fireEvent.change(textarea, { target: { value: 'abc' } });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verify-error-alert')).toBeInTheDocument();
        expect(screen.getByText('Nội dung quá ngắn.')).toBeInTheDocument();
        expect(textarea).toHaveValue('abc');
      });
    });

    it('displays friendly error message on HTTP 500 server exception', async () => {
      vi.spyOn(verificationService, 'verifyText').mockRejectedValueOnce(
        new ApiClientError('Server crash', 500)
      );

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), { target: { value: 'Lỗi server' } });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verify-error-alert')).toBeInTheDocument();
        expect(screen.getByText(/máy chủ đang gặp sự cố/i)).toBeInTheDocument();
      });
    });

    it('displays network failure message when connection is broken (statusCode 0)', async () => {
      vi.spyOn(verificationService, 'verifyText').mockRejectedValueOnce(
        new ApiClientError('Network fail', 0)
      );

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), { target: { value: 'Mất mạng' } });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verify-error-alert')).toBeInTheDocument();
        expect(screen.getByText(/không thể kết nối đến máy chủ/i)).toBeInTheDocument();
      });
    });

    it('handles claim without evidences gracefully with fallback state', async () => {
      const resultWithoutEvidence: VerificationResultResponse = {
        request_id: 'req-no-ev',
        status: 'COMPLETED',
        overall_verdict: 'UNVERIFIED',
        claims_count: 1,
        claims: [
          {
            claim_id: 'claim-sparse',
            claim_text: 'Nhận định này chưa có bằng chứng.',
            verdict: 'NOT_ENOUGH_INFO',
            confidence_score: 0.1,
            evidences: [],
          },
        ],
        created_at: '2026-09-14T10:00:00Z',
      };

      vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(resultWithoutEvidence);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), { target: { value: 'Claim thiếu bằng chứng' } });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verified-claim-claim-sparse')).toBeInTheDocument();
      });

      expect(screen.getByTestId('claim-no-evidence-claim-sparse')).toHaveTextContent(
        'Không có bằng chứng trực tiếp đính kèm'
      );
    });

    it('handles response with empty claims gracefully without crashing', async () => {
      const resultEmptyClaims: VerificationResultResponse = {
        request_id: 'req-empty-claims',
        status: 'COMPLETED',
        overall_verdict: 'UNVERIFIED',
        claims_count: 0,
        claims: [],
        created_at: '2026-09-14T10:00:00Z',
      };

      vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(resultEmptyClaims);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), { target: { value: 'Không trích xuất được claim' } });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });

      expect(screen.getByTestId('empty-claims-notice')).toBeInTheDocument();
      expect(screen.getByTestId('claims-count-tag')).toHaveTextContent('0 claims');
    });

    it('clicking sample claim in empty state populates input and triggers verify', async () => {
      const verifySpy = vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(mockVerificationResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      const sampleBtn = screen.getByTestId('sample-claim-0');
      fireEvent.click(sampleBtn);

      expect(verifySpy).toHaveBeenCalledTimes(1);
      expect(verifySpy).toHaveBeenCalledWith(
        expect.objectContaining({
          text: expect.stringContaining('WTO'),
        })
      );

      await waitFor(() => {
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });
    });
  });

  describe('5. Extract Claims Flow (FE-04.2)', () => {
    it('switches to Extract Claims tab and renders composer and empty state', () => {
      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      // Click tab Extract Claims
      const extractTab = screen.getByTestId('tab-extract-claims');
      fireEvent.click(extractTab);

      // Verify Tab is active
      expect(extractTab).toHaveClass('active');

      // Verify Extract Composer
      expect(screen.getByTestId('extract-textarea')).toBeInTheDocument();
      expect(screen.getByTestId('btn-extract-claims')).toBeInTheDocument();

      // Verify Empty State
      expect(screen.getByTestId('extract-empty-state')).toBeInTheDocument();
      expect(screen.getByText('Phân tách văn bản thành các nhận định kiểm chứng')).toBeInTheDocument();
      expect(screen.getByTestId('sample-extract-0')).toBeInTheDocument();
    });

    it('disables Extract Claims button when input is empty and enables when text is entered', () => {
      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('tab-extract-claims'));

      const textarea = screen.getByTestId('extract-textarea');
      const extractBtn = screen.getByTestId('btn-extract-claims');

      // Empty -> disabled
      expect(extractBtn).toBeDisabled();

      // Whitespace only -> disabled
      fireEvent.change(textarea, { target: { value: '   ' } });
      expect(extractBtn).toBeDisabled();

      // Meaningful text -> enabled
      fireEvent.change(textarea, { target: { value: 'Đoạn văn bản để trích xuất nhận định sự thật.' } });
      expect(extractBtn).not.toBeDisabled();
    });

    it('calls verificationService.extractClaims with accurate payload on submit', async () => {
      const extractSpy = vi.spyOn(verificationService, 'extractClaims').mockResolvedValueOnce(mockClaimExtractResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('tab-extract-claims'));

      const textarea = screen.getByTestId('extract-textarea');
      const extractBtn = screen.getByTestId('btn-extract-claims');

      fireEvent.change(textarea, { target: { value: 'Việt Nam gia nhập WTO năm 2007 sau 11 năm đàm phán.' } });
      fireEvent.click(extractBtn);

      expect(extractSpy).toHaveBeenCalledTimes(1);
      expect(extractSpy).toHaveBeenCalledWith({
        text: 'Việt Nam gia nhập WTO năm 2007 sau 11 năm đàm phán.',
        max_claims: 10,
      });

      await waitFor(() => {
        expect(screen.getByTestId('extract-results-container')).toBeInTheDocument();
      });
    });

    it('triggers extraction via Ctrl+Enter shortcut', async () => {
      const extractSpy = vi.spyOn(verificationService, 'extractClaims').mockResolvedValueOnce(mockClaimExtractResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('tab-extract-claims'));

      const textarea = screen.getByTestId('extract-textarea');
      fireEvent.change(textarea, { target: { value: 'Phím tắt trích xuất claims' } });
      fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });

      expect(extractSpy).toHaveBeenCalledTimes(1);

      await waitFor(() => {
        expect(screen.getByTestId('extract-results-container')).toBeInTheDocument();
      });
    });

    it('displays loading state and disables action while extract request is pending', async () => {
      let resolvePromise: (val: any) => void;
      const deferred = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      vi.spyOn(verificationService, 'extractClaims').mockImplementationOnce(() => deferred as any);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('tab-extract-claims'));

      const textarea = screen.getByTestId('extract-textarea');
      const extractBtn = screen.getByTestId('btn-extract-claims');

      fireEvent.change(textarea, { target: { value: 'Đang trích xuất dữ liệu...' } });
      fireEvent.click(extractBtn);

      // Loading state visible
      expect(screen.getByTestId('extract-loading-state')).toBeInTheDocument();
      expect(screen.getByText(/đang phân tích cấu trúc ngữ nghĩa/i)).toBeInTheDocument();
      expect(extractBtn).toBeDisabled();

      // Resolve API
      resolvePromise!(mockClaimExtractResult);

      await waitFor(() => {
        expect(screen.queryByTestId('extract-loading-state')).not.toBeInTheDocument();
        expect(screen.getByTestId('extract-results-container')).toBeInTheDocument();
      });
    });

    it('renders extracted claims with order, text, context sentence, and verifiable status', async () => {
      vi.spyOn(verificationService, 'extractClaims').mockResolvedValueOnce(mockClaimExtractResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('tab-extract-claims'));
      fireEvent.change(screen.getByTestId('extract-textarea'), { target: { value: 'Test render claims' } });
      fireEvent.click(screen.getByTestId('btn-extract-claims'));

      await waitFor(() => {
        expect(screen.getByTestId('extract-results-container')).toBeInTheDocument();
      });

      // Total count badge
      expect(screen.getByTestId('extract-claims-count')).toHaveTextContent('2 claims');

      // Claim 1
      const claim1 = screen.getByTestId('extracted-claim-claim_1');
      expect(within(claim1).getByTestId('extracted-claim-order-claim_1')).toHaveTextContent('#1');
      expect(within(claim1).getByTestId('extracted-claim-text-claim_1')).toHaveTextContent(
        'Việt Nam chính thức trở thành thành viên WTO năm 2007'
      );
      expect(within(claim1).getByTestId('extracted-claim-context-claim_1')).toHaveTextContent(
        'Việt Nam gia nhập WTO năm 2007 sau 11 năm đàm phán'
      );
      expect(within(claim1).getByTestId('extracted-claim-verifiable-claim_1')).toHaveTextContent(
        'Có thể kiểm chứng thực nghiệm'
      );

      // Claim 2
      const claim2 = screen.getByTestId('extracted-claim-claim_2');
      expect(within(claim2).getByTestId('extracted-claim-order-claim_2')).toHaveTextContent('#2');
      expect(within(claim2).getByTestId('extracted-claim-text-claim_2')).toHaveTextContent(
        'Quá trình đàm phán gia nhập WTO của Việt Nam kéo dài 11 năm'
      );
    });

    it('handles empty extracted claims response gracefully with notice', async () => {
      const emptyClaimsResponse: ClaimExtractResponse = {
        total_claims: 0,
        claims: [],
      };

      vi.spyOn(verificationService, 'extractClaims').mockResolvedValueOnce(emptyClaimsResponse);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('tab-extract-claims'));
      fireEvent.change(screen.getByTestId('extract-textarea'), { target: { value: 'Văn bản không có claim' } });
      fireEvent.click(screen.getByTestId('btn-extract-claims'));

      await waitFor(() => {
        expect(screen.getByTestId('extract-results-container')).toBeInTheDocument();
      });

      expect(screen.getByTestId('extract-empty-notice')).toHaveTextContent(
        'Không tìm thấy nhận định thực tế nào từ đoạn văn bản đã nhập'
      );
      expect(screen.getByTestId('extract-claims-count')).toHaveTextContent('0 claims');
    });

    it('displays error alert on HTTP 422 without clearing user input during extract', async () => {
      vi.spyOn(verificationService, 'extractClaims').mockRejectedValueOnce(
        new ApiClientError('Văn bản trích xuất quá ngắn.', 422)
      );

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('tab-extract-claims'));

      const textarea = screen.getByTestId('extract-textarea');
      fireEvent.change(textarea, { target: { value: 'ngan' } });
      fireEvent.click(screen.getByTestId('btn-extract-claims'));

      await waitFor(() => {
        expect(screen.getByTestId('extract-error-alert')).toBeInTheDocument();
        expect(screen.getByText('Văn bản trích xuất quá ngắn.')).toBeInTheDocument();
        expect(textarea).toHaveValue('ngan');
      });
    });

    it('clicking sample text in empty state populates input and triggers extractClaims', async () => {
      const extractSpy = vi.spyOn(verificationService, 'extractClaims').mockResolvedValueOnce(mockClaimExtractResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('tab-extract-claims'));

      const sampleBtn = screen.getByTestId('sample-extract-0');
      fireEvent.click(sampleBtn);

      expect(extractSpy).toHaveBeenCalledTimes(1);
      expect(extractSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          text: expect.stringContaining('WTO'),
        })
      );

      await waitFor(() => {
        expect(screen.getByTestId('extract-results-container')).toBeInTheDocument();
      });
    });

    it('clicking "Kiểm chứng nhận định này" transfers claim text to Verify tab', async () => {
      vi.spyOn(verificationService, 'extractClaims').mockResolvedValueOnce(mockClaimExtractResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      // Go to Extract Claims tab and execute
      fireEvent.click(screen.getByTestId('tab-extract-claims'));
      fireEvent.change(screen.getByTestId('extract-textarea'), { target: { value: 'Sample for bridge' } });
      fireEvent.click(screen.getByTestId('btn-extract-claims'));

      await waitFor(() => {
        expect(screen.getByTestId('extracted-claim-claim_1')).toBeInTheDocument();
      });

      // Click "Kiểm chứng nhận định này" on Claim 1
      const bridgeBtn = screen.getByTestId('btn-verify-claim-claim_1');
      fireEvent.click(bridgeBtn);

      // Verify that active tab switched back to Verify tab
      expect(screen.getByTestId('tab-verify')).toHaveClass('active');

      // Verify that the verify textarea was pre-populated with the claim text
      const verifyTextarea = screen.getByTestId('factcheck-textarea') as HTMLTextAreaElement;
      expect(verifyTextarea).toBeInTheDocument();
      expect(verifyTextarea.value).toBe('Việt Nam chính thức trở thành thành viên WTO năm 2007.');
      expect(screen.getByTestId('btn-verify')).not.toBeDisabled();
    });
  });

  describe('5. Stance Grouping & Evidence Drawer (FE-04.3)', () => {
    const mockMultiStanceVerificationResult: VerificationResultResponse = {
      request_id: 'req-multi-stance-001',
      status: 'COMPLETED',
      overall_verdict: 'MIXED',
      summary: 'Mixed factual results with conflicting stances.',
      claims_count: 2,
      claims: [
        {
          claim_id: 'claim-multi-01',
          claim_text: 'Tăng trưởng kinh tế quý 1 đạt 10% theo công bố chính thức.',
          verdict: 'MIXED',
          confidence_score: 0.82,
          explanation: 'Các nguồn cung cấp số liệu đối nghịch nhau.',
          evidences: [
            {
              evidence_id: 'ev-sup-1',
              source_title: 'Báo Đầu Tư',
              source_url: 'https://baodautu.vn/gdp-q1',
              publisher: 'Bộ Kế hoạch và Đầu tư',
              snippet: 'Theo số liệu ước tính ban đầu, tốc độ tăng trưởng có thể tiệm cận 10%.',
              stance: 'SUPPORTS',
              quote: 'Tốc độ tăng trưởng có thể tiệm cận 10%.',
              relevance_score: 0.91,
            },
            {
              evidence_id: 'ev-ref-1',
              source_title: 'Tổng cục Thống kê (GSO)',
              source_url: 'https://gso.gov.vn/gdp-q1-official',
              publisher: 'Tổng cục Thống kê',
              snippet: 'Tăng trưởng GDP quý 1 thực tế ghi nhận mức 5.66%, không phải 10%.',
              stance: 'REFUTES',
              quote: 'Tăng trưởng GDP quý 1 thực tế ghi nhận mức 5.66%, không phải 10%.',
              relevance_score: 0.98,
            },
            {
              evidence_id: 'ev-neu-1',
              source_title: 'Báo cáo Ngân hàng Thế giới',
              source_url: 'https://worldbank.org/vn-economic-monitor',
              publisher: 'World Bank',
              snippet: 'Bối cảnh kinh tế vĩ mô toàn cầu tác động đến chỉ số quý 1.',
              stance: 'NEUTRAL',
              quote: 'Bối cảnh kinh tế vĩ mô toàn cầu biến động.',
              relevance_score: 0.75,
            },
          ],
        },
        {
          claim_id: 'claim-empty-02',
          claim_text: 'Một nhận định không có bằng chứng tham chiếu cụ thể.',
          verdict: 'UNVERIFIABLE',
          confidence_score: 0.2,
          explanation: 'Không có tài liệu kiểm chứng nào trong cơ sở tri thức.',
          evidences: [],
        },
      ],
      created_at: '2026-09-14T10:00:00Z',
      completed_at: '2026-09-14T10:00:02Z',
    };

    it('groups evidences by stance (SUPPORTS, REFUTES, NEUTRAL) with proper badges and counts', async () => {
      vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(mockMultiStanceVerificationResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), {
        target: { value: 'Tăng trưởng kinh tế quý 1 đạt 10% theo công bố chính thức.' },
      });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });

      // Check stance groups for claim-multi-01
      const supportsGroup = screen.getByTestId('stance-group-claim-multi-01-supports');
      expect(supportsGroup).toBeInTheDocument();
      expect(within(supportsGroup).getByText(/Ủng hộ \(Supports\)/i)).toBeInTheDocument();

      const refutesGroup = screen.getByTestId('stance-group-claim-multi-01-refutes');
      expect(refutesGroup).toBeInTheDocument();
      expect(within(refutesGroup).getByText(/Mâu thuẫn \/ Phản bác \(Refutes \/ Contradicts\)/i)).toBeInTheDocument();

      const neutralGroup = screen.getByTestId('stance-group-claim-multi-01-neutral');
      expect(neutralGroup).toBeInTheDocument();
      expect(within(neutralGroup).getByText(/Trung lập \/ Bối cảnh \(Neutral\)/i)).toBeInTheDocument();

      // Check empty evidences fallback for claim-empty-02
      expect(screen.getByTestId('claim-no-evidence-claim-empty-02')).toBeInTheDocument();
      expect(screen.getByText('Không có bằng chứng trực tiếp đính kèm')).toBeInTheDocument();
    });

    it('opens evidence drawer on evidence card click and displays complete details', async () => {
      vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(mockMultiStanceVerificationResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), {
        target: { value: 'Tăng trưởng kinh tế quý 1 đạt 10% theo công bố chính thức.' },
      });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });

      // Drawer is initially closed
      expect(screen.queryByTestId('fc-evidence-drawer')).not.toBeInTheDocument();

      // Click on the REFUTES evidence card (global index 1)
      const refutesCard = screen.getByTestId('claim-evidence-claim-multi-01-1');
      fireEvent.click(refutesCard);

      // Drawer should now be visible
      const drawer = screen.getByTestId('fc-evidence-drawer');
      expect(drawer).toBeInTheDocument();

      // Verify drawer header & stance
      expect(screen.getByTestId('fc-drawer-header-stance')).toHaveTextContent('● REFUTES');
      expect(screen.getByTestId('fc-drawer-claim-text')).toHaveTextContent(
        'Tăng trưởng kinh tế quý 1 đạt 10% theo công bố chính thức.'
      );
      expect(screen.getByTestId('fc-drawer-stance-badge')).toHaveTextContent('● REFUTES');
      expect(screen.getByText(/phản bác\/mâu thuẫn với nhận định/i)).toBeInTheDocument();

      // Verify source info & publisher
      expect(screen.getByTestId('fc-drawer-source-title')).toHaveTextContent('Tổng cục Thống kê (GSO)');
      expect(screen.getByTestId('fc-drawer-publisher')).toHaveTextContent('Tổng cục Thống kê');
      const sourceLink = screen.getByTestId('fc-drawer-source-url');
      expect(sourceLink).toHaveAttribute('href', 'https://gso.gov.vn/gdp-q1-official');

      // Verify verbatim quote, snippet, and relevance score
      expect(screen.getByTestId('fc-drawer-quote')).toHaveTextContent(
        'Tăng trưởng GDP quý 1 thực tế ghi nhận mức 5.66%, không phải 10%.'
      );
      expect(screen.getByTestId('fc-drawer-snippet')).toHaveTextContent(
        'Tăng trưởng GDP quý 1 thực tế ghi nhận mức 5.66%, không phải 10%.'
      );
      expect(screen.getByTestId('fc-drawer-relevance')).toHaveTextContent('98%');
      expect(screen.getByTestId('fc-drawer-evidence-id')).toHaveTextContent('ev-ref-1');
    });

    it('opens drawer via "Xem chi tiết đối chiếu" button and closes via close button', async () => {
      vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(mockMultiStanceVerificationResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), {
        target: { value: 'Tăng trưởng kinh tế quý 1 đạt 10% theo công bố chính thức.' },
      });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });

      // Click inspect button on SUPPORTS evidence (global index 0)
      const inspectBtn = screen.getByTestId('btn-inspect-evidence-claim-multi-01-0');
      fireEvent.click(inspectBtn);

      expect(screen.getByTestId('fc-evidence-drawer')).toBeInTheDocument();
      expect(screen.getByTestId('fc-drawer-header-stance')).toHaveTextContent('● SUPPORTS');
      expect(screen.getByText(/ủng hộ\/xác nhận nhận định/i)).toBeInTheDocument();

      // Close using the close button
      const closeBtn = screen.getByTestId('fc-drawer-close-btn');
      fireEvent.click(closeBtn);

      expect(screen.queryByTestId('fc-evidence-drawer')).not.toBeInTheDocument();
    });

    it('closes drawer when clicking backdrop or pressing Escape key', async () => {
      vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(mockMultiStanceVerificationResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), {
        target: { value: 'Tăng trưởng kinh tế quý 1 đạt 10% theo công bố chính thức.' },
      });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });

      // 1. Open drawer and close with backdrop
      fireEvent.click(screen.getByTestId('claim-evidence-claim-multi-01-2')); // NEUTRAL evidence
      expect(screen.getByTestId('fc-evidence-drawer')).toBeInTheDocument();

      const backdrop = screen.getByTestId('fc-evidence-drawer-backdrop');
      fireEvent.click(backdrop);
      expect(screen.queryByTestId('fc-evidence-drawer')).not.toBeInTheDocument();

      // 2. Open drawer again and close with Escape key
      fireEvent.click(screen.getByTestId('claim-evidence-claim-multi-01-2'));
      expect(screen.getByTestId('fc-evidence-drawer')).toBeInTheDocument();

      fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
      expect(screen.queryByTestId('fc-evidence-drawer')).not.toBeInTheDocument();
    });

    it('gracefully handles evidence missing optional fields (no quote, snippet, url, or publisher)', async () => {
      const mockSparseEvidenceResult: VerificationResultResponse = {
        request_id: 'req-sparse-001',
        status: 'COMPLETED',
        overall_verdict: 'FALSE',
        summary: 'Sparse test result.',
        claims_count: 1,
        claims: [
          {
            claim_id: 'claim-sparse-01',
            claim_text: 'Nhận định với bằng chứng tối giản.',
            verdict: 'REFUTED',
            confidence_score: 0.9,
            explanation: 'Bằng chứng không có quote và snippet.',
            evidences: [
              {
                source_title: 'Nguồn rút gọn',
                stance: 'REFUTES',
                snippet: '',
                relevance_score: 0,
              },
            ],
          },
        ],
        created_at: '2026-09-14T10:00:00Z',
        completed_at: '2026-09-14T10:00:01Z',
      };

      vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(mockSparseEvidenceResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), {
        target: { value: 'Nhận định với bằng chứng tối giản.' },
      });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });

      // Click sparse evidence card
      fireEvent.click(screen.getByTestId('claim-evidence-claim-sparse-01-0'));

      expect(screen.getByTestId('fc-evidence-drawer')).toBeInTheDocument();
      expect(screen.getByTestId('fc-drawer-source-title')).toHaveTextContent('Nguồn rút gọn');
      // Quote and snippet should not be rendered, fallback message displayed
      expect(screen.queryByTestId('fc-drawer-quote')).not.toBeInTheDocument();
      expect(screen.queryByTestId('fc-drawer-snippet')).not.toBeInTheDocument();
      expect(screen.getByTestId('fc-drawer-no-content')).toBeInTheDocument();
      expect(screen.queryByTestId('fc-drawer-publisher')).not.toBeInTheDocument();
      expect(screen.queryByTestId('fc-drawer-source-url')).not.toBeInTheDocument();
      expect(screen.queryByTestId('fc-drawer-relevance')).not.toBeInTheDocument();
    });
  });

  describe('6. Comprehensive Verification Labels & Multi-Claim Inspection (CHAT-04.7B)', () => {
    const mockComprehensiveResult: VerificationResultResponse = {
      request_id: 'req-multi-001',
      status: 'COMPLETED',
      overall_verdict: 'MIXED',
      summary: 'Báo cáo tổng hợp: một số nhận định chính xác, một số nhận định sai lệch hoặc chưa đủ căn cứ.',
      claims_count: 4,
      claims: [
        {
          claim_id: 'claim-c1',
          claim_text: 'Việt Nam gia nhập WTO vào năm 2007.',
          verdict: 'SUPPORTED',
          confidence_score: 0.98,
          explanation: 'Tài liệu xác nhận ngày gia nhập.',
          evidences: [
            {
              evidence_id: 'ev-c1',
              source_title: 'Văn kiện WTO',
              snippet: 'Việt Nam chính thức là thành viên WTO năm 2007.',
              stance: 'SUPPORTS',
              quote: 'Gia nhập năm 2007.',
              relevance_score: 0.96,
            },
          ],
        },
        {
          claim_id: 'claim-c2',
          claim_text: 'Tăng trưởng GDP năm 2023 đạt trên 10%.',
          verdict: 'REFUTED',
          confidence_score: 0.95,
          explanation: 'Báo cáo Tổng cục Thống kê ghi nhận tăng trưởng đạt 5.05%, không phải trên 10%.',
          evidences: [
            {
              evidence_id: 'ev-c2',
              source_title: 'Tổng cục Thống kê',
              snippet: 'Tăng trưởng GDP năm 2023 đạt 5.05%.',
              stance: 'REFUTES',
              quote: 'GDP năm 2023 tăng 5.05%.',
              relevance_score: 0.93,
            },
          ],
        },
        {
          claim_id: 'claim-c3',
          claim_text: 'Kim ngạch xuất khẩu nông sản có xu hướng tăng mạnh.',
          verdict: 'PARTIALLY_SUPPORTED',
          confidence_score: 0.75,
          explanation: 'Tăng trưởng ở một số mặt hàng chủ lực như gạo và sầu riêng, nhưng thủy sản giảm nhẹ.',
          evidences: [
            {
              evidence_id: 'ev-c3',
              source_title: 'Báo Nông nghiệp',
              snippet: 'Xuất khẩu gạo và rau quả tăng kỷ lục, thủy sản gặp khó khăn.',
              stance: 'SUPPORTS',
              relevance_score: 0.82,
            },
          ],
        },
        {
          claim_id: 'claim-c4',
          claim_text: 'Dự báo tăng trưởng năm 2035 sẽ đạt 15%.',
          verdict: 'NOT_ENOUGH_INFO',
          confidence_score: 0.2,
          explanation: 'Không có tài liệu đáng tin cậy dự báo số liệu cho mốc thời gian này.',
          evidences: [],
        },
      ],
      created_at: '2026-09-15T08:00:00Z',
    };

    it('displays all 4 claim labels (SUPPORTED, PARTIALLY_SUPPORTED, REFUTED, NOT_ENOUGH_INFO) correctly', async () => {
      vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(mockComprehensiveResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), {
        target: { value: 'Kiểm chứng đoạn văn bản tổng hợp đa nhận định.' },
      });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('verify-results-container')).toBeInTheDocument();
      });

      // Overall Verdict
      expect(screen.getByTestId('overall-verdict-badge')).toHaveTextContent(/MIXED/i);

      // Claim 1: SUPPORTED
      expect(screen.getByTestId('claim-verdict-claim-c1')).toHaveTextContent(/SUPPORTED/i);
      expect(screen.getByTestId('claim-evidence-claim-c1-0')).toBeInTheDocument();

      // Claim 2: REFUTED
      expect(screen.getByTestId('claim-verdict-claim-c2')).toHaveTextContent(/REFUTED/i);
      expect(screen.getByTestId('claim-evidence-claim-c2-0')).toBeInTheDocument();

      // Claim 3: PARTIALLY_SUPPORTED
      expect(screen.getByTestId('claim-verdict-claim-c3')).toHaveTextContent(/PARTIALLY_SUPPORTED/i);

      // Claim 4: NOT_ENOUGH_INFO with no evidence notice
      expect(screen.getByTestId('claim-verdict-claim-c4')).toHaveTextContent(/NOT_ENOUGH_INFO/i);
      expect(screen.getByTestId('claim-no-evidence-claim-c4')).toBeInTheDocument();
    });

    it('opens and closes evidence drawer when inspecting corroborating evidence', async () => {
      vi.spyOn(verificationService, 'verifyText').mockResolvedValueOnce(mockComprehensiveResult);

      render(
        <MemoryRouter>
          <FactCheckPage />
        </MemoryRouter>
      );

      fireEvent.change(screen.getByTestId('factcheck-textarea'), {
        target: { value: 'Kiểm tra mở bảng chi tiết bằng chứng.' },
      });
      fireEvent.click(screen.getByTestId('btn-verify'));

      await waitFor(() => {
        expect(screen.getByTestId('claim-evidence-claim-c2-0')).toBeInTheDocument();
      });

      // Click inspect button on claim 2 evidence
      fireEvent.click(screen.getByTestId('btn-inspect-evidence-claim-c2-0'));

      expect(screen.getByTestId('fc-evidence-drawer')).toBeInTheDocument();
      expect(screen.getByTestId('fc-drawer-source-title')).toHaveTextContent('Tổng cục Thống kê');
      expect(screen.getByTestId('fc-drawer-quote')).toHaveTextContent('GDP năm 2023 tăng 5.05%.');

      // Close drawer via close button
      fireEvent.click(screen.getByTestId('fc-drawer-close-btn'));

      expect(screen.queryByTestId('fc-evidence-drawer')).not.toBeInTheDocument();
    });
  });
});
