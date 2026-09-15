/**
 * FactCheckPage: Core Fact-Checking workspace for SourceCheck AI (FE-04.1 & FE-04.2).
 * Supports both Full Fact-Check Verification and Atomic Claims Extraction flows.
 */

import React, { useState } from 'react';
import { verificationService } from '../services/verification';
import { VerificationResultResponse, ClaimExtractResponse, VerificationEvidenceItem } from '../types/verification';
import { ApiClientError } from '../services/apiClient';
import { useAIPreferences } from '../hooks/useAIPreferences';
import { FactCheckEvidenceDrawer } from '../components/factCheck/FactCheckEvidenceDrawer';
import '../styles/factCheck.css';

const SAMPLE_CLAIMS = [
  'Việt Nam chính thức gia nhập Tổ chức Thương mại Thế giới (WTO) vào năm 2007.',
  'Tốc độ tăng trưởng GDP của Việt Nam năm 2023 đạt mức kỷ lục 20%.',
  'Hà Nội là thủ đô của nước Cộng hòa Xã hội Chủ nghĩa Việt Nam.',
];

const SAMPLE_TEXTS_FOR_EXTRACTION = [
  'Việt Nam gia nhập WTO năm 2007 sau 11 năm đàm phán, đồng thời kim ngạch xuất nhập khẩu đã tăng trưởng mạnh mẽ trong các năm tiếp theo.',
  'Trí tuệ nhân tạo đang phát triển nhanh chóng và tạo ra nhiều cơ hội việc làm mới, tuy nhiên cũng đòi hỏi nâng cao kỹ năng lao động.',
];

export const FactCheckPage: React.FC = () => {
  const { t } = useAIPreferences();
  // Active Tab: 'verify' (Full Fact-Checking) | 'extract' (Claim Extraction)
  const [activeTab, setActiveTab] = useState<'verify' | 'extract'>('verify');

  // --- Verify Flow State ---
  const [text, setText] = useState<string>('');
  const [sourceUrl, setSourceUrl] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerificationResultResponse | null>(null);

  // --- Extract Claims Flow State ---
  const [extractText, setExtractText] = useState<string>('');
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [extractResult, setExtractResult] = useState<ClaimExtractResponse | null>(null);

  // --- Evidence Drawer State (FE-04.3) ---
  const [selectedEvidence, setSelectedEvidence] = useState<VerificationEvidenceItem | null>(null);
  const [selectedEvidenceClaimText, setSelectedEvidenceClaimText] = useState<string>('');
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);

  const handleOpenEvidence = (ev: VerificationEvidenceItem, claimText?: string) => {
    setSelectedEvidence(ev);
    setSelectedEvidenceClaimText(claimText || '');
    setIsDrawerOpen(true);
  };

  const handleCloseEvidence = () => {
    setIsDrawerOpen(false);
    setSelectedEvidence(null);
  };

  // --- Verify Handlers ---
  const handleVerify = async (textToSubmit?: string) => {
    const claimContent = (textToSubmit ?? text).trim();
    if (!claimContent || isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await verificationService.verifyText({
        text: claimContent,
        source_url: sourceUrl.trim() || undefined,
        enable_contradiction_check: true,
        top_k_evidence: 5,
      });
      setResult(response);
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        if (err.statusCode === 401) {
          setError('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại để tiếp tục.');
        } else if (err.statusCode === 422) {
          setError(err.message || 'Nội dung kiểm chứng phải có tối thiểu 5 ký tự hợp lệ.');
        } else if (err.statusCode >= 500) {
          setError('Máy chủ đang gặp sự cố khi xử lý kiểm chứng. Vui lòng thử lại sau.');
        } else if (err.statusCode === 0) {
          setError('Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.');
        } else {
          setError(err.message || 'Đã xảy ra lỗi trong quá trình xử lý kiểm chứng.');
        }
      } else {
        setError(err?.message || 'Đã xảy ra lỗi không xác định.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // --- Extract Claims Handlers ---
  const handleExtract = async (textToExtract?: string) => {
    const content = (textToExtract ?? extractText).trim();
    if (!content || isExtracting) return;

    setIsExtracting(true);
    setExtractError(null);

    try {
      const response = await verificationService.extractClaims({
        text: content,
        max_claims: 10,
      });
      setExtractResult(response);
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        if (err.statusCode === 401) {
          setExtractError('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại để tiếp tục.');
        } else if (err.statusCode === 422) {
          setExtractError(err.message || 'Nội dung trích xuất phải có tối thiểu 5 ký tự hợp lệ.');
        } else if (err.statusCode >= 500) {
          setExtractError('Máy chủ đang gặp sự cố khi trích xuất nhận định. Vui lòng thử lại sau.');
        } else if (err.statusCode === 0) {
          setExtractError('Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.');
        } else {
          setExtractError(err.message || 'Đã xảy ra lỗi trong quá trình trích xuất nhận định.');
        }
      } else {
        setExtractError(err?.message || 'Đã xảy ra lỗi không xác định.');
      }
    } finally {
      setIsExtracting(false);
    }
  };

  const handleSelectClaimForVerify = (claimText: string) => {
    setText(claimText);
    setActiveTab('verify');
  };

  const overallVerdict = result?.overall_verdict || 'UNVERIFIED';
  const verdictClass = overallVerdict.toLowerCase();

  return (
    <div className="factcheck-container" data-testid="fact-check-page">
      {/* Page Header */}
      <div className="factcheck-header">
        <h1>{t('fc.pageTitle')}</h1>
        <p>{t('fc.pageDescription')}</p>
      </div>

      {/* Tabs Navigation */}
      <div className="factcheck-tabs" role="tablist">
        <button
          type="button"
          className={`factcheck-tab-btn ${activeTab === 'verify' ? 'active' : ''}`}
          onClick={() => setActiveTab('verify')}
          role="tab"
          aria-selected={activeTab === 'verify'}
          data-testid="tab-verify"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <path d="m9 12 2 2 4-4" />
          </svg>
          <span>{t('fc.tabVerify')}</span>
        </button>

        <button
          type="button"
          className={`factcheck-tab-btn ${activeTab === 'extract' ? 'active' : ''}`}
          onClick={() => setActiveTab('extract')}
          role="tab"
          aria-selected={activeTab === 'extract'}
          data-testid="tab-extract-claims"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
          <span>{t('fc.tabExtract')}</span>
        </button>
      </div>

      {/* =========================================================================
          TAB 1: FULL VERIFY FLOW (FE-04.1)
          ========================================================================= */}
      {activeTab === 'verify' && (
        <>
          {/* Input Composer Card */}
          <div className="factcheck-composer-card" data-testid="factcheck-composer">
            <textarea
              className="factcheck-textarea"
              placeholder="Nhập nội dung, tuyên bố hoặc đoạn tin tức cần kiểm chứng (ví dụ: 'Năm 2007 Việt Nam gia nhập WTO')..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                  e.preventDefault();
                  handleVerify();
                }
              }}
              disabled={isLoading}
              rows={3}
              aria-label="Nội dung cần kiểm chứng"
              data-testid="factcheck-textarea"
            />

            <div className="factcheck-url-input-wrap">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
              </svg>
              <input
                type="url"
                className="factcheck-url-input"
                placeholder="URL nguồn gốc (tùy chọn, ví dụ: https://baochinhphu.vn/...)"
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                disabled={isLoading}
                aria-label="URL nguồn gốc"
                data-testid="factcheck-url-input"
              />
            </div>

            <div className="composer-footer">
              <span className="composer-hint">
                <kbd>Ctrl</kbd> + <kbd>Enter</kbd> để kiểm chứng
              </span>

              <button
                type="button"
                className="btn-verify"
                onClick={() => handleVerify()}
                disabled={!text.trim() || isLoading}
                aria-label="Verify Content"
                data-testid="btn-verify"
              >
                {isLoading ? (
                  <>
                    <span className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                    <span>{t('fc.verifyingBtn')}</span>
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                    <span>{t('fc.verifyBtn')}</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="verify-error-alert" role="alert" data-testid="verify-error-alert">
              <span>{error}</span>
              <button
                type="button"
                onClick={() => setError(null)}
                style={{ background: 'none', border: 'none', color: '#991b1b', cursor: 'pointer', fontWeight: 'bold' }}
                aria-label="Đóng thông báo lỗi"
              >
                ✕
              </button>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="verify-loading-card" data-testid="verify-loading-state">
              <div className="spinner" style={{ width: '36px', height: '36px', borderWidth: '3px', borderTopColor: '#2563eb' }} />
              <p className="verify-loading-text">
                Đang trích xuất nhận định, truy xuất bằng chứng và phân tích lập trường...
              </p>
            </div>
          )}

          {/* Empty State */}
          {!result && !isLoading && !error && (
            <div className="verify-empty-state" data-testid="verify-empty-state">
              <svg
                className="verify-empty-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <h3>Sẵn sàng đối soát và kiểm chứng tin tức</h3>
              <p>
                Nhập nội dung cần kiểm chứng ở trên hoặc chọn các tuyên bố mẫu dưới đây.
                SourceCheck AI sẽ tự động phân rã văn bản thành các luận điểm độc lập, đối soát với nguồn tư liệu bảo chứng và đưa ra kết luận.
              </p>

              <div className="sample-claims-list">
                {SAMPLE_CLAIMS.map((sampleClaim, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="sample-claim-btn"
                    onClick={() => {
                      setText(sampleClaim);
                      handleVerify(sampleClaim);
                    }}
                    data-testid={`sample-claim-${idx}`}
                  >
                    <span>{sampleClaim}</span>
                    <span style={{ color: 'var(--color-primary)' }}>&rarr;</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Results Section */}
          {result && !isLoading && (
            <div className="verify-results-container" data-testid="verify-results-container">
              {/* Overall Verdict Card */}
              <div className="overall-verdict-card" data-testid="overall-verdict-card">
                <div className="overall-verdict-header">
                  <h2 className="overall-verdict-title">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                    <span>Kết luận kiểm chứng tổng thể</span>
                  </h2>

                  <span className={`verdict-badge ${verdictClass}`} data-testid="overall-verdict-badge">
                    ● {overallVerdict}
                  </span>
                </div>

                {result.summary && (
                  <p className="overall-summary" data-testid="overall-summary-text">
                    {result.summary}
                  </p>
                )}

                <div className="result-meta-row">
                  <span className="meta-item" data-testid="meta-request-id">
                    Mã yêu cầu: {result.request_id}
                  </span>
                  <span className="meta-item" data-testid="meta-status">
                    Trạng thái: {result.status}
                  </span>
                  <span className="meta-item" data-testid="meta-claims-count">
                    Số nhận định: {result.claims_count ?? result.claims?.length ?? 0}
                  </span>
                  {result.created_at && (
                    <span className="meta-item" data-testid="meta-created-at">
                      Thời gian: {new Date(result.created_at).toLocaleString('vi-VN')}
                    </span>
                  )}
                </div>
              </div>

              {/* Verified Claims Section */}
              <div className="verified-claims-section" data-testid="verified-claims-section">
                <div className="verified-claims-header">
                  <span>Danh sách nhận định đã xác minh</span>
                  <span className="claims-count-tag" data-testid="claims-count-tag">
                    {result.claims?.length || 0} claims
                  </span>
                </div>

                {result.claims && result.claims.length > 0 ? (
                  <div className="claims-cards-list" data-testid="verified-claims-list">
                    {result.claims.map((claim, idx) => {
                      const claimKey = claim.claim_id || `claim-${idx + 1}`;
                      const claimVerdict = claim.verdict || 'UNVERIFIED';
                      const claimVerdictClass = claimVerdict.toLowerCase();

                      return (
                        <div
                          key={claimKey}
                          className="claim-card"
                          data-testid={`verified-claim-${claimKey}`}
                        >
                          <div className="claim-card-top">
                            <span className="claim-order-num">#{idx + 1}</span>
                            <p className="claim-card-text" data-testid={`claim-text-${claimKey}`}>
                              {claim.claim_text}
                            </p>
                            <div className="claim-card-badges">
                              <span
                                className={`claim-verdict-tag ${claimVerdictClass}`}
                                data-testid={`claim-verdict-${claimKey}`}
                              >
                                ● {claimVerdict}
                              </span>
                              {typeof claim.confidence_score === 'number' && (
                                <span
                                  className="claim-confidence-tag"
                                  data-testid={`claim-confidence-${claimKey}`}
                                >
                                  Độ tin cậy: {Math.round(claim.confidence_score * 100)}%
                                </span>
                              )}
                            </div>
                          </div>

                          {claim.explanation && (
                            <div
                              className="claim-explanation-box"
                              data-testid={`claim-explanation-${claimKey}`}
                            >
                              <strong>Giải thích:</strong> {claim.explanation}
                            </div>
                          )}

                          {/* Evidence attached to claim */}
                          <div
                            className="claim-evidences-box"
                            data-testid={`claim-evidences-${claimKey}`}
                          >
                            <span className="claim-evidences-title">
                              Bằng chứng đối chiếu ({claim.evidences?.length || 0}):
                            </span>

                            {claim.evidences && claim.evidences.length > 0 ? (
                              <div className="claim-evidences-grouped">
                                {(['SUPPORTS', 'REFUTES', 'NEUTRAL'] as const).map((targetStance) => {
                                  const matchingEvidences = claim.evidences.filter(
                                    (e) => (e.stance || 'NEUTRAL').toUpperCase() === targetStance
                                  );
                                  if (matchingEvidences.length === 0) return null;

                                  const stanceLabel =
                                    targetStance === 'SUPPORTS'
                                      ? 'Ủng hộ (Supports)'
                                      : targetStance === 'REFUTES'
                                      ? 'Mâu thuẫn / Phản bác (Refutes / Contradicts)'
                                      : 'Trung lập / Bối cảnh (Neutral)';

                                  return (
                                    <div
                                      key={targetStance}
                                      className="stance-group"
                                      data-testid={`stance-group-${claimKey}-${targetStance.toLowerCase()}`}
                                    >
                                      <div className="stance-group-header">
                                        <span className={`stance-pill ${targetStance.toLowerCase()}`}>
                                          ● {targetStance}
                                        </span>
                                        <span>{stanceLabel}</span>
                                        <span className="stance-group-count">
                                          {matchingEvidences.length}
                                        </span>
                                      </div>

                                      {matchingEvidences.map((ev) => {
                                        const globalEvIdx = claim.evidences.indexOf(ev);
                                        const stanceClass = (ev.stance || 'neutral').toLowerCase();

                                        return (
                                          <div
                                            key={ev.evidence_id || `ev-${claimKey}-${globalEvIdx}`}
                                            className={`evidence-item-card clickable ${stanceClass}`}
                                            data-testid={`claim-evidence-${claimKey}-${globalEvIdx}`}
                                            onClick={() => handleOpenEvidence(ev, claim.claim_text)}
                                          >
                                            <div className="evidence-item-top">
                                              {ev.stance && (
                                                <span
                                                  className={`stance-pill ${stanceClass}`}
                                                  data-testid={`evidence-stance-${claimKey}-${globalEvIdx}`}
                                                >
                                                  {ev.stance}
                                                </span>
                                              )}
                                              <span className="evidence-source-title">{ev.source_title}</span>
                                              {ev.source_url && (
                                                <a
                                                  href={ev.source_url}
                                                  target="_blank"
                                                  rel="noopener noreferrer"
                                                  className="evidence-source-link"
                                                  onClick={(e) => e.stopPropagation()}
                                                  data-testid={`evidence-source-url-${claimKey}-${globalEvIdx}`}
                                                >
                                                  Xem nguồn &rarr;
                                                </a>
                                              )}
                                            </div>

                                            {(ev.quote || ev.snippet) && (
                                              <p className="evidence-quote-snippet">
                                                &ldquo;{ev.quote || ev.snippet}&rdquo;
                                              </p>
                                            )}

                                            <div className="evidence-actions-bar">
                                              <button
                                                type="button"
                                                className="btn-inspect-evidence"
                                                onClick={(e) => {
                                                  e.stopPropagation();
                                                  handleOpenEvidence(ev, claim.claim_text);
                                                }}
                                                data-testid={`btn-inspect-evidence-${claimKey}-${globalEvIdx}`}
                                                aria-label="Xem chi tiết bằng chứng"
                                              >
                                                <span>Xem chi tiết đối chiếu</span>
                                                <span>&rarr;</span>
                                              </button>

                                              {typeof ev.relevance_score === 'number' && ev.relevance_score > 0 && (
                                                <span className="evidence-relevance-score">
                                                  Độ khớp: {Math.round(ev.relevance_score * 100)}%
                                                </span>
                                              )}
                                            </div>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  );
                                })}

                                {/* Other unclassified stances if backend returns custom stance */}
                                {claim.evidences
                                  .filter(
                                    (e) =>
                                      !['SUPPORTS', 'REFUTES', 'NEUTRAL'].includes(
                                        (e.stance || '').toUpperCase()
                                      )
                                  )
                                  .map((ev) => {
                                    const globalEvIdx = claim.evidences.indexOf(ev);
                                    return (
                                      <div
                                        key={ev.evidence_id || `ev-other-${claimKey}-${globalEvIdx}`}
                                        className="evidence-item-card clickable neutral"
                                        data-testid={`claim-evidence-${claimKey}-${globalEvIdx}`}
                                        onClick={() => handleOpenEvidence(ev, claim.claim_text)}
                                      >
                                        <div className="evidence-item-top">
                                          <span className="stance-pill neutral">{ev.stance}</span>
                                          <span className="evidence-source-title">{ev.source_title}</span>
                                        </div>
                                        {(ev.quote || ev.snippet) && (
                                          <p className="evidence-quote-snippet">
                                            &ldquo;{ev.quote || ev.snippet}&rdquo;
                                          </p>
                                        )}
                                      </div>
                                    );
                                  })}
                              </div>
                            ) : (
                              <span
                                className="claim-no-evidence-text"
                                data-testid={`claim-no-evidence-${claimKey}`}
                              >
                                Không có bằng chứng trực tiếp đính kèm
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div
                    style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--color-text-muted)', fontSize: '0.9rem' }}
                    data-testid="empty-claims-notice"
                  >
                    Không có nhận định độc lập nào được trích xuất từ nội dung đã nhập.
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* =========================================================================
          TAB 2: EXTRACT CLAIMS FLOW (FE-04.2)
          ========================================================================= */}
      {activeTab === 'extract' && (
        <>
          {/* Extract Claims Composer Card */}
          <div className="factcheck-composer-card" data-testid="extract-composer">
            <textarea
              className="factcheck-textarea"
              placeholder="Nhập một đoạn văn bản hoặc tin tức tổng hợp để trích xuất các luận điểm độc lập (Claims)..."
              value={extractText}
              onChange={(e) => setExtractText(e.target.value)}
              onKeyDown={(e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                  e.preventDefault();
                  handleExtract();
                }
              }}
              disabled={isExtracting}
              rows={4}
              aria-label="Đoạn văn bản cần trích xuất nhận định"
              data-testid="extract-textarea"
            />

            <div className="composer-footer">
              <span className="composer-hint">
                <kbd>Ctrl</kbd> + <kbd>Enter</kbd> để trích xuất
              </span>

              <button
                type="button"
                className="btn-verify"
                onClick={() => handleExtract()}
                disabled={!extractText.trim() || isExtracting}
                aria-label="Extract Claims"
                data-testid="btn-extract-claims"
              >
                {isExtracting ? (
                  <>
                    <span className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                    <span>{t('fc.extractingBtn')}</span>
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                      <polyline points="10 9 9 9 8 9" />
                    </svg>
                    <span>{t('fc.extractBtn')}</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Extract Error Alert */}
          {extractError && (
            <div className="verify-error-alert" role="alert" data-testid="extract-error-alert">
              <span>{extractError}</span>
              <button
                type="button"
                onClick={() => setExtractError(null)}
                style={{ background: 'none', border: 'none', color: '#991b1b', cursor: 'pointer', fontWeight: 'bold' }}
                aria-label="Đóng thông báo lỗi trích xuất"
              >
                ✕
              </button>
            </div>
          )}

          {/* Extract Loading State */}
          {isExtracting && (
            <div className="verify-loading-card" data-testid="extract-loading-state">
              <div className="spinner" style={{ width: '36px', height: '36px', borderWidth: '3px', borderTopColor: '#2563eb' }} />
              <p className="verify-loading-text">
                Đang phân tích cấu trúc ngữ nghĩa và trích xuất các nhận định độc lập (Atomic Claims)...
              </p>
            </div>
          )}

          {/* Extract Empty State */}
          {!extractResult && !isExtracting && !extractError && (
            <div className="verify-empty-state" data-testid="extract-empty-state">
              <svg
                className="verify-empty-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              <h3>Phân tách văn bản thành các nhận định kiểm chứng</h3>
              <p>
                Dán một đoạn văn bản hoặc tin tức phức hợp. Hệ thống sẽ bóc tách các mệnh đề sự thật độc lập,
                giúp bạn dễ dàng đối soát từng thông tin trước khi kiểm chứng toàn diện.
              </p>

              <div className="sample-claims-list">
                {SAMPLE_TEXTS_FOR_EXTRACTION.map((sampleText, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="sample-claim-btn"
                    onClick={() => {
                      setExtractText(sampleText);
                      handleExtract(sampleText);
                    }}
                    data-testid={`sample-extract-${idx}`}
                  >
                    <span>{sampleText}</span>
                    <span style={{ color: 'var(--color-primary)' }}>&rarr;</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Extract Results Section */}
          {extractResult && !isExtracting && (
            <div className="extracted-claims-section" data-testid="extract-results-container">
              <div className="extracted-claims-header">
                <h2 className="extracted-claims-header-title">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                  </svg>
                  <span>Các nhận định được trích xuất (Atomic Claims)</span>
                </h2>
                <span className="claims-count-tag" data-testid="extract-claims-count">
                  {extractResult.total_claims ?? extractResult.claims?.length ?? 0} claims
                </span>
              </div>

              {extractResult.claims && extractResult.claims.length > 0 ? (
                <div className="extracted-claims-list" data-testid="extracted-claims-list">
                  {extractResult.claims.map((claim, idx) => {
                    const claimKey = claim.claim_id || `extracted-${idx + 1}`;
                    const isVerifiable = claim.verifiable !== false;

                    return (
                      <div
                        key={claimKey}
                        className="extracted-claim-card"
                        data-testid={`extracted-claim-${claimKey}`}
                      >
                        <div className="extracted-claim-top">
                          <span
                            className="extracted-claim-order"
                            data-testid={`extracted-claim-order-${claimKey}`}
                          >
                            #{idx + 1}
                          </span>

                          <div className="extracted-claim-body">
                            <p
                              className="extracted-claim-text"
                              data-testid={`extracted-claim-text-${claimKey}`}
                            >
                              {claim.claim_text}
                            </p>

                            {claim.context_sentence && (
                              <p
                                className="extracted-claim-context"
                                data-testid={`extracted-claim-context-${claimKey}`}
                              >
                                Ngữ cảnh gốc: &ldquo;{claim.context_sentence}&rdquo;
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="extracted-claim-actions-row">
                          <span
                            className={`extracted-verifiable-badge ${isVerifiable ? 'verifiable' : 'non-verifiable'}`}
                            data-testid={`extracted-claim-verifiable-${claimKey}`}
                          >
                            {isVerifiable ? '● Có thể kiểm chứng thực nghiệm' : '○ Khó kiểm chứng thực nghiệm'}
                          </span>

                          <button
                            type="button"
                            className="btn-verify-claim-link"
                            onClick={() => handleSelectClaimForVerify(claim.claim_text)}
                            title="Chuyển nhận định này sang chế độ kiểm chứng toàn diện"
                            aria-label={`Kiểm chứng nhận định ${idx + 1}`}
                            data-testid={`btn-verify-claim-${claimKey}`}
                          >
                            <span>Kiểm chứng nhận định này &rarr;</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div
                  style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--color-text-muted)', fontSize: '0.9rem' }}
                  data-testid="extract-empty-notice"
                >
                  Không tìm thấy nhận định thực tế nào từ đoạn văn bản đã nhập.
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Evidence Detail Drawer (FE-04.3) */}
      <FactCheckEvidenceDrawer
        isOpen={isDrawerOpen}
        onClose={handleCloseEvidence}
        evidence={selectedEvidence}
        claimText={selectedEvidenceClaimText}
      />
    </div>
  );
};
