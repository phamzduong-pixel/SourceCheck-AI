/**
 * QAPage: Core Grounded Question Answering workspace for SourceCheck AI.
 * Handles question composing, API dispatch, provenance rendering, and evidence inspection.
 */

import React, { useEffect, useState } from 'react';
import { qaService } from '../services/qa';
import { FinalAnswerResponse, CitationItem, QuestionRequest, QATaskType } from '../types/qa';
import { documentService } from '../services/documents';
import { DocumentResponse } from '../types/document';
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
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [taskType, setTaskType] = useState<QATaskType>('qa');
  const [submittedDocumentIds, setSubmittedDocumentIds] = useState<string[]>([]);
  const [submittedTaskType, setSubmittedTaskType] = useState<QATaskType>('qa');
  const [isDocumentsLoading, setIsDocumentsLoading] = useState<boolean>(true);
  const [documentLoadError, setDocumentLoadError] = useState<string | null>(null);

  // Evidence Drawer State
  const [activeCitation, setActiveCitation] = useState<CitationItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;

    const loadDocuments = async () => {
      try {
        const response = await documentService.listDocuments({ page: 1, page_size: 100 });
        if (isMounted) {
          setDocuments(response.items);
          setDocumentLoadError(null);
        }
      } catch (err: any) {
        // Document loading must not disable the existing unscoped Q&A flow.
        if (isMounted) {
          setDocumentLoadError(err?.message || 'Unable to load available documents.');
        }
      } finally {
        if (isMounted) setIsDocumentsLoading(false);
      }
    };

    loadDocuments();
    return () => {
      isMounted = false;
    };
  }, []);

  const toggleDocument = (documentId: string) => {
    setSelectedDocumentIds((currentIds) => {
      if (taskType === 'summary') {
        return currentIds[0] === documentId ? [] : [documentId];
      }
      return currentIds.includes(documentId)
        ? currentIds.filter((id) => id !== documentId)
        : [...currentIds, documentId];
    });
  };

  const handleTaskTypeChange = (nextTaskType: QATaskType) => {
    setTaskType(nextTaskType);
    if (nextTaskType === 'summary') {
      setSelectedDocumentIds((currentIds) => currentIds.slice(0, 1));
    }
  };

  const handleAsk = async (queryText?: string) => {
    const textToSubmit = (queryText ?? question).trim();
    if (!textToSubmit || isLoading) return;

    const scopeForRequest = [...selectedDocumentIds];
    if (taskType === 'summary' && scopeForRequest.length !== 1) {
      setError('Chọn đúng một tài liệu trước khi tạo tóm tắt.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSubmittedDocumentIds(scopeForRequest);
    setSubmittedTaskType(taskType);

    const request: QuestionRequest = {
      question: textToSubmit,
      top_k: 5,
      search_mode: 'hybrid',
    };
    if (taskType === 'summary') {
      request.task_type = 'summary';
      request.document_ids = scopeForRequest;
    } else if (scopeForRequest.length > 0) {
      request.document_ids = scopeForRequest;
    }

    try {
      const response = await qaService.askQuestion(request);
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
  const isSummaryResult =
    submittedTaskType === 'summary' || result?.metadata?.task_type === 'summary';
  const summaryDocument = documents.find(
    (document) => document.id === submittedDocumentIds[0]
  );
  const documentChunksTotal = result?.metadata?.document_chunks_total;
  const documentChunksProcessed = result?.metadata?.document_chunks_processed;
  const documentCoverage = result?.metadata?.document_coverage;
  const summaryClaimCoverage = result?.metadata?.summary_claim_coverage;
  const hasPartialDocumentProcessing =
    isSummaryResult &&
    typeof documentCoverage === 'number' &&
    documentCoverage < 1;

  return (
    <div className="qa-container" data-testid="qa-page">
      {/* Page Header */}
      <div className="qa-page-header">
        <h1>{t('qa.pageTitle')}</h1>
        <p>{t('qa.pageDescription')}</p>
      </div>

      {/* Question Composer Card */}
      <div className="question-composer-card" data-testid="question-composer">
                <fieldset
          data-testid="qa-operation-selector"
          style={{
            margin: '0 0 1rem',
            padding: '0.85rem',
            border: '1px solid var(--color-border, #e5e7eb)',
            borderRadius: '0.75rem',
          }}
        >
          <legend style={{ padding: '0 0.25rem', fontWeight: 600 }}>Operation</legend>
          <label style={{ marginRight: '1rem', cursor: 'pointer' }}>
            <input
              type="radio"
              name="qa-task-type"
              value="qa"
              checked={taskType === 'qa'}
              onChange={() => handleTaskTypeChange('qa')}
              disabled={isLoading}
              data-testid="operation-qa"
            />
            {' '}Q&amp;A
          </label>
          <label style={{ cursor: 'pointer' }}>
            <input
              type="radio"
              name="qa-task-type"
              value="summary"
              checked={taskType === 'summary'}
              onChange={() => handleTaskTypeChange('summary')}
              disabled={isLoading}
              data-testid="operation-summary"
            />
            {' '}Summary
          </label>
          {taskType === 'summary' && (
            <p data-testid="summary-operation-hint" style={{ margin: '0.6rem 0 0', color: 'var(--color-text-muted)' }}>
              Summary uses every available chunk from one selected document and verifies its claims with citations.
            </p>
          )}
        </fieldset>

        <div
          data-testid="document-scope-selector"
          style={{
            marginBottom: '1rem',
            padding: '0.85rem',
            border: '1px solid var(--color-border, #e5e7eb)',
            borderRadius: '0.75rem',
            background: 'var(--color-surface-muted, #f8fafc)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '0.6rem' }}>
            <strong>{taskType === 'summary' ? 'Document to summarize' : 'Documents for this question'}</strong>
            <span data-testid="selected-document-count" style={{ color: 'var(--color-text-muted)' }}>
              {selectedDocumentIds.length > 0
                ? selectedDocumentIds.length + ' selected'
                : taskType === 'summary' ? 'Select one document' : 'No document scope'}
            </span>
          </div>

          {isDocumentsLoading ? (
            <span data-testid="documents-loading">Loading available documents...</span>
          ) : documents.length > 0 ? (
            <div role="group" aria-label={taskType === 'summary' ? 'Select one document for summary' : 'Select documents for Q&A'}>
              {documents.map((document) => (
                <label
                  key={document.id}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.45rem', cursor: 'pointer' }}
                >
                  <input
                    type={taskType === 'summary' ? 'radio' : 'checkbox'}
                    name={taskType === 'summary' ? 'summary-document' : undefined}
                    checked={selectedDocumentIds.includes(document.id)}
                    onChange={() => toggleDocument(document.id)}
                    disabled={isLoading}
                    data-testid={'document-checkbox-' + document.id}
                  />
                  <span>{document.title}</span>
                </label>
              ))}
            </div>
          ) : (
            <span data-testid="documents-empty">No uploaded documents available.</span>
          )}

          {documentLoadError && (
            <p data-testid="documents-load-error" style={{ margin: '0.5rem 0 0', color: 'var(--color-text-muted)' }}>
              {documentLoadError}
            </p>
          )}

          {selectedDocumentIds.length > 0 && (
            <p data-testid="active-document-scope" style={{ margin: '0.65rem 0 0', color: 'var(--color-primary)' }}>
              {taskType === 'summary' ? 'Summarizing: ' : 'Using: '}{documents
                .filter((document) => selectedDocumentIds.includes(document.id))
                .map((document) => document.title)
                .join(', ')}
            </p>
          )}
        </div>
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
            disabled={!question.trim() || isLoading || (taskType === 'summary' && selectedDocumentIds.length !== 1)}
            aria-label={taskType === 'summary' ? 'Summarize Document' : 'Ask Question'}
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
                <span>{taskType === 'summary' ? 'Summarize document' : t('qa.composerAskBtn')}</span>
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
          {submittedDocumentIds.length > 0 && (
            <div data-testid="submitted-document-scope" style={{ marginBottom: '0.75rem', color: 'var(--color-text-muted)' }}>
              {isSummaryResult ? 'Summary document: ' : 'Answer scoped to: '}{documents
                .filter((document) => submittedDocumentIds.includes(document.id))
                .map((document) => document.title)
                .join(', ')}
            </div>
          )}

          {isSummaryResult && (
            <div
              data-testid="summary-grounding-metadata"
              style={{
                marginBottom: '0.75rem',
                padding: '0.85rem',
                border: '1px solid var(--color-border, #e5e7eb)',
                borderRadius: '0.75rem',
                background: 'var(--color-surface-muted, #f8fafc)',
              }}
            >
              <strong data-testid="summary-document-title">
                Summarizing: {summaryDocument?.title || submittedDocumentIds[0] || 'Selected document'}
              </strong>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.8rem', marginTop: '0.55rem', color: 'var(--color-text-muted)' }}>
                {typeof documentChunksProcessed === 'number' && typeof documentChunksTotal === 'number' && (
                  <span data-testid="summary-chunks-processed">
                    Chunks processed: {documentChunksProcessed}/{documentChunksTotal}
                  </span>
                )}
                {typeof documentCoverage === 'number' && (
                  <span data-testid="summary-document-coverage">
                    Document coverage: {Math.round(documentCoverage * 100)}%
                  </span>
                )}
                {typeof summaryClaimCoverage === 'number' && (
                  <span data-testid="summary-claim-coverage">
                    Claim coverage: {Math.round(summaryClaimCoverage * 100)}%
                  </span>
                )}
              </div>
              <p data-testid="summary-grounding-status" style={{ margin: '0.55rem 0 0' }}>
                {result.status === 'INSUFFICIENT_EVIDENCE'
                  ? 'Insufficient evidence: this summary could not be fully grounded in the selected document.'
                  : hasPartialDocumentProcessing
                    ? 'Partial summary: one or more document batches were not processed successfully.'
                    : 'Grounded summary: claims and citations were verified against the selected document.'}
              </p>
            </div>
          )}

          {/* Main Answer Card */}
          <div className="qa-answer-card">
            <div className="answer-card-header">
              <h2 className="answer-card-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <path d="m9 12 2 2 4-4" />
                </svg>
                <span>{isSummaryResult ? 'Document Summary' : t('qa.answerTitle')}</span>
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