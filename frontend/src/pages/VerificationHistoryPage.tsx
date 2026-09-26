import React, { useCallback, useEffect, useState } from 'react';
import { verificationService } from '../services/verification';
import {
  VerificationHistoryItem,
  VerificationResultResponse,
} from '../types/verification';
import { VerificationResultCard } from '../components/qa/VerificationResultCard';
import { ApiClientError } from '../services/apiClient';
import '../styles/verificationHistory.css';
import '../styles/qa.css';

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));

export const VerificationHistoryPage: React.FC = () => {
  const [items, setItems] = useState<VerificationHistoryItem[]>([]);
  const [selectedReport, setSelectedReport] = useState<VerificationResultResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await verificationService.getHistory();
      setItems(response.items);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Không thể tải lịch sử kiểm chứng.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const handleViewResult = async (item: VerificationHistoryItem) => {
    setIsLoadingReport(true);
    setReportError(null);
    try {
      const report = await verificationService.getVerificationReport(item.request_id);
      setSelectedReport(report);
    } catch (err) {
      setReportError(err instanceof ApiClientError ? err.message : 'Kết quả kiểm chứng này không còn khả dụng.');
    } finally {
      setIsLoadingReport(false);
    }
  };

  return (
    <main className="verification-history-page" data-testid="verification-history-page">
      <header className="verification-history-header">
        <h1>Lịch sử kiểm chứng</h1>
        <p>Xem lại các câu trả lời đã được đối chiếu với nguồn tài liệu.</p>
      </header>

      {selectedReport ? (
        <section className="verification-history-detail" data-testid="verification-history-detail">
          <button type="button" className="history-back-button" onClick={() => setSelectedReport(null)}>
            ← Quay lại lịch sử
          </button>
          <VerificationResultCard report={selectedReport} />
        </section>
      ) : (
        <section className="verification-history-list" aria-live="polite">
          {isLoading && <p className="history-state">Đang tải lịch sử kiểm chứng...</p>}
          {!isLoading && error && (
            <div className="history-state history-error" role="alert">
              <p>{error}</p>
              <button type="button" onClick={() => void loadHistory()}>Thử lại</button>
            </div>
          )}
          {!isLoading && !error && items.length === 0 && (
            <div className="history-state" data-testid="verification-history-empty">
              <h2>Chưa có kết quả kiểm chứng</h2>
              <p>Khi bạn hỏi một câu có dẫn nguồn, kết quả sẽ xuất hiện ở đây.</p>
            </div>
          )}
          {!isLoading && !error && items.map((item) => (
            <article className="verification-history-item" key={item.request_id} data-testid={`verification-history-item-${item.request_id}`}>
              <div className="history-item-content">
                <div className="history-item-meta">
                  <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
                  <span className={`claim-verdict-pill ${item.overall_verdict.toLowerCase()}`}>{item.overall_verdict}</span>
                </div>
                <h2>{item.question}</h2>
                {item.answer_preview && <p className="history-answer-preview">{item.answer_preview}</p>}
                <span className="history-coverage">Evidence Coverage: {Math.round(item.evidence_coverage * 100)}%</span>
              </div>
              <button type="button" className="history-view-button" onClick={() => void handleViewResult(item)}>
                Xem kết quả
              </button>
            </article>
          ))}
          {isLoadingReport && <p className="history-state">Đang mở kết quả kiểm chứng...</p>}
          {reportError && <p className="history-state history-error" role="alert">{reportError}</p>}
        </section>
      )}
    </main>
  );
};
