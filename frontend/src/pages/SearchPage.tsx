/**
 * SearchPage: Search & Retrieval Explorer Page (FE-04.6B).
 * Enables independent query testing, retriever selection (Hybrid, Vector, BM25),
 * Cross-Encoder reranking toggle, and transparent inspection of the RAG pipeline.
 */

import React, { useState } from 'react';
import { searchService } from '../services/search';
import { SearchResponse, SearchHit } from '../types/search';
import { useAIPreferences } from '../hooks/useAIPreferences';
import { ApiClientError } from '../services/apiClient';
import { SearchResultCard } from '../components/search/SearchResultCard';
import { RetrievalDetailsDrawer } from '../components/search/RetrievalDetailsDrawer';
import '../styles/search.css';

const SAMPLE_QUERIES = [
  'Nghị định 13 bảo vệ dữ liệu cá nhân',
  'Tốc độ tăng trưởng GDP Việt Nam năm 2024',
  'Quy định về dữ liệu cá nhân nhạy cảm',
  'Luật An ninh mạng và lưu trữ dữ liệu tại Việt Nam',
];

export const SearchPage: React.FC = () => {
  const { t } = useAIPreferences();
  // Search parameters state
  const [query, setQuery] = useState<string>('');
  const mode: 'hybrid' = 'hybrid';
  const rerank = true;
  const topK = 5;

  // Execution & UI state
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [lastExecutedQuery, setLastExecutedQuery] = useState<string>('');

  // Selected hit for Retrieval Details Drawer
  const [selectedHit, setSelectedHit] = useState<SearchHit | null>(null);

  const executeSearch = async (
    targetQuery = query,
    targetMode = mode,
    targetRerank = rerank,
    targetTopK = topK
  ) => {
    const trimmed = targetQuery.trim();
    if (!trimmed) return;

    setIsLoading(true);
    setError(null);
    setLastExecutedQuery(trimmed);

    try {
      const response = await searchService.search(
        {
          query: trimmed,
          top_k: targetTopK,
          mode: targetMode,
          rerank: targetRerank,
        },
        targetMode,
        targetRerank
      );

      setSearchResponse(response);
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        if (err.statusCode === 401) {
          setError('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.');
        } else if (err.statusCode >= 500) {
          setError('Máy chủ gặp lỗi khi thực thi retrieval (500). Vui lòng thử lại sau.');
        } else if (err.statusCode === 0) {
          setError('Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại kết nối mạng.');
        } else {
          setError(err.message || 'Lỗi khi thực hiện tìm kiếm.');
        }
      } else {
        setError(err?.message || 'Đã xảy ra lỗi không xác định trong quá trình retrieval.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch();
  };

  const handleSampleQueryClick = (sample: string) => {
    setQuery(sample);
    executeSearch(sample, mode, rerank, topK);
  };

  return (
    <div className="search-explorer-container" data-testid="search-page">
      {/* Page Header */}
      <div className="search-header">
<h1>{t('search.title')}</h1>
        <p>{t('search.description')}</p>
      </div>

      {/* Search Input & Options Card */}
      <div className="search-controls-card">
        <form className="search-input-form" onSubmit={handleFormSubmit} data-testid="search-form">
          <div className="search-input-wrapper">
            <div className="search-icon-decor">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </div>
            <input
              type="text"
              className="search-input"
              placeholder={t('search.placeholder')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isLoading}
              data-testid="search-query-input"
            />
            <button
              type="submit"
              className="btn-search-submit"
              disabled={isLoading || !query.trim()}
              data-testid="btn-execute-search"
            >
              {isLoading ? (
                <>
                  <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                  <span>{t('search.loading')}</span>
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                  <span>{t('search.submit')}</span>
                </>
              )}
            </button>
          </div>

          {/* Sample Queries Chips */}
          <div className="sample-queries-wrap" data-testid="sample-queries-wrap">
            <span className="sample-queries-label">{t('search.suggestions')}</span>
            {SAMPLE_QUERIES.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                className="sample-chip"
                onClick={() => handleSampleQueryClick(sample)}
                disabled={isLoading}
                data-testid={`sample-query-chip-${idx}`}
              >
                {sample}
              </button>
            ))}
          </div>
        </form>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="search-alert danger" role="alert" data-testid="search-error-alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} className="alert-close-btn" data-testid="btn-close-error">
            ✕
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="search-loading-state" data-testid="search-loading-state">
          <div className="spinner" style={{ width: '36px', height: '36px', borderWidth: '3px' }} />
          <p>{t('search.loading')}</p>
        </div>
      )}

      {/* Initial Empty State */}
      {!isLoading && !searchResponse && !error && (
        <div className="search-empty-state" data-testid="search-initial-state">
          <div className="empty-icon-wrap">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h3>{t('search.initialTitle')}</h3>
          <p>{t('search.initialDescription')}</p>

        </div>
      )}

      {/* Zero Results State */}
      {!isLoading && searchResponse && searchResponse.hits.length === 0 && (
        <div className="search-empty-state" data-testid="search-zero-results-state">
          <div className="empty-icon-wrap">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h3>Không tìm thấy kết quả phù hợp</h3>
          <p>
            Không có đoạn trích nào trong cơ sở tri thức khớp với câu truy vấn <strong>"{searchResponse.query}"</strong>.
            Thử nạp thêm tài liệu hoặc thay đổi từ khóa tìm kiếm.
          </p>
        </div>
      )}

      {/* Results Section */}
      {!isLoading && searchResponse && searchResponse.hits.length > 0 && (
        <div className="search-results-section" data-testid="search-results-section">
          {/* Stats & Metadata Strip */}
          <div className="search-stats-strip" data-testid="search-stats-strip">
            <div className="stats-left">
              <span>
                Tìm thấy <strong>{searchResponse.total_hits}</strong> kết quả cho <em>"{searchResponse.query}"</em>
              </span>
            </div>
          </div>

          {/* Hits List */}
          <div className="search-results-list" data-testid="search-results-list">
            {searchResponse.hits.map((hit, index) => (
              <SearchResultCard
                key={hit.chunk_id || index}
                hit={hit}
                index={index}
                onViewDetails={(selected) => setSelectedHit(selected)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Retrieval Details Drawer */}
      {selectedHit && (
        <RetrievalDetailsDrawer
          isOpen={!!selectedHit}
          onClose={() => setSelectedHit(null)}
          hit={selectedHit}
          query={lastExecutedQuery || searchResponse?.query}
        />
      )}
    </div>
  );
};
