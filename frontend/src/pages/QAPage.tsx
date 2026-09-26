/**
 * QAPage: Core Grounded Question Answering workspace for SourceCheck AI.
 * Handles question composing, API dispatch, provenance rendering, and evidence inspection.
 */

import React, { useState } from 'react';
import { qaService } from '../services/qa';
import { FinalAnswerResponse, CitationItem } from '../types/qa';
import { ApiClientError } from '../services/apiClient';
import { AnswerRenderer } from '../components/qa/AnswerRenderer';
import { EvidenceCoverageCard } from '../components/qa/EvidenceCoverageCard';
import { ClaimList } from '../components/qa/ClaimList';
import { EvidenceDrawer } from '../components/qa/EvidenceDrawer';
import { useAIPreferences } from '../hooks/useAIPreferences';
import '../styles/qa.css';

const SAMPLE_QUESTIONS = [
  'Việt Nam chính thức gia nhập Tổ chức Thương mại Thế giới (WTO) vào năm nào?',
  'Chính phủ Việt Nam đã ban hành chiến lược phát triển kinh tế số như thế nào?',
  'Quy định pháp luật hiện hành về an toàn an ninh mạng tại Việt Nam gồm những nội dung gì?',
];

export const QAPage: React.FC = () => {
  const { t, showSources, showVerification } = useAIPreferences();
  const [question, setQuestion] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FinalAnswerResponse | null>(null);

  // Evidence Drawer State
  const [activeCitation, setActiveCitation] = useState<CitationItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);

  const handleAsk = async (queryText?: string) => {
    const textToSubmit = (queryText ?? question).trim();
    if (!textToSubmit || isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await qaService.askQuestion({
        question: textToSubmit,
        top_k: 5,
        search_mode: 'hybrid',
      });
      setResult(response);
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        if (err.statusCode === 401) {
          setError('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại để tiếp tục.');
        } else if (err.statusCode === 422) {
          setError(err.message || 'Dữ liệu câu hỏi không hợp lệ.');
        } else if (err.statusCode >= 500) {
          setError('Máy chủ đang gặp sự cố khi xử lý câu hỏi. Vui lòng thử lại sau.');
        } else if (err.statusCode === 0) {
          setError('Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.');
        } else {
          setError(err.message || 'Đã xảy ra lỗi trong quá trình xử lý câu hỏi.');
        }
      } else {
        setError(err?.message || 'Đã xảy ra lỗi không xác định.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleAsk();
    }
  };

  const handleCitationClick = (citation: CitationItem) => {
    setActiveCitation(citation);
    setIsDrawerOpen(true);
  };

  // Find corresponding evidence item for active citation
  const activeEvidence = result?.evidence?.find(
    (ev) => ev.evidence_id === activeCitation?.evidence_id
  );

  return (
    <div className="qa-container" data-testid="qa-page">
      {/* Page Header */}
      <div className="qa-page-header">
        <h1>{t('qa.pageTitle')}</h1>
        <p>{t('qa.pageDescription')}</p>
      </div>

      {/* Question Composer Card */}
      <div className="question-composer-card" data-testid="question-composer">
        <textarea
          className="question-textarea"
          placeholder={t('qa.composerPlaceholder')}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          rows={2}
          aria-label="Nhập câu hỏi"
          data-testid="question-textarea"
        />

        <div className="composer-controls">
          <span className="composer-hint">
            <kbd>Ctrl</kbd> + <kbd>Enter</kbd> {t('qa.composerHint')}
          </span>

          <button
            type="button"
            className="btn-ask"
            onClick={() => handleAsk()}
            disabled={!question.trim() || isLoading}
            aria-label="Ask Question"
            data-testid="btn-ask"
          >
            {isLoading ? (
              <>
                <span className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                <span>{t('qa.composerAskingBtn')}</span>
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
                <span>{t('qa.composerAskBtn')}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="qa-error-alert" role="alert" data-testid="qa-error-alert">
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

      {/* Loading State Skeleton */}
      {isLoading && (
        <div className="qa-loading-card" data-testid="qa-loading-state">
          <div className="spinner" style={{ width: '36px', height: '36px', borderWidth: '3px', borderTopColor: 'var(--color-primary)' }} />
          <p className="qa-loading-text">
            {t('qa.loadingTitle')}
          </p>
        </div>
      )}

      {/* Answer Result Section */}
      {result && !isLoading && (
        <div className="qa-answer-container" data-testid="qa-answer-container">
          {/* Main Answer Card */}
          <div className="qa-answer-card">
            <div className="answer-card-header">
              <h2 className="answer-card-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <path d="m9 12 2 2 4-4" />
                </svg>
                <span>{t('qa.answerTitle')}</span>
              </h2>

              <span
                className={`status-pill ${(result.status || 'supported').toLowerCase()}`}
                data-testid="answer-status-pill"
              >
                ● {result.status}
              </span>
            </div>

            {/* Answer Text with Interactive Citations */}
            <AnswerRenderer
              answerText={result.answer}
              citations={showSources ? result.citations || [] : []}
              onCitationClick={handleCitationClick}
              showCitations={showSources}
            />
          </div>

          {/* Evidence Coverage Card */}
          {showVerification && typeof result.evidence_coverage === 'number' && (
            <EvidenceCoverageCard
              coverage={result.evidence_coverage}
              status={result.status}
              summary={result.verification_summary}
              totalClaims={result.claims?.length}
            />
          )}

          {/* Claims Breakdown Section */}
          {showVerification && result.claims && result.claims.length > 0 && (
            <ClaimList
              claims={result.claims}
              citations={showSources ? result.citations || [] : []}
              onCitationClick={handleCitationClick}
            />
          )}
        </div>
      )}

      {/* Empty State (Shown when no question asked yet) */}
      {!result && !isLoading && !error && (
        <div className="qa-empty-state" data-testid="qa-empty-state">
          <svg
            className="qa-empty-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            <path d="M9 10h.01" />
            <path d="M15 10h.01" />
            <path d="M12 10h.01" />
          </svg>
          <h3>{t('qa.emptyTitle')}</h3>
          <p>{t('qa.emptyDescription')}</p>

          <div className="sample-questions-list">
            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '0.25rem', textAlign: 'left' }}>
              Gợi ý câu hỏi mẫu:
            </div>
            {SAMPLE_QUESTIONS.map((sampleQ, idx) => (
              <button
                key={idx}
                type="button"
                className="sample-question-btn"
                onClick={() => {
                  setQuestion(sampleQ);
                  handleAsk(sampleQ);
                }}
                data-testid={`sample-question-${idx}`}
              >
                <span>{sampleQ}</span>
                <span style={{ color: 'var(--color-primary)' }}>&rarr;</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Drawer */}
      <EvidenceDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        citation={activeCitation}
        evidence={activeEvidence}
      />
    </div>
  );
};