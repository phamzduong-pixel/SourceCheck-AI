/**
 * SearchResultCard: Displays an individual retrieval hit with rank, scores,
 * provenance metadata, and action to inspect the pipeline breakdown.
 */

import React from 'react';
import { SearchHit } from '../../types/search';
import { useAIPreferences } from '../../hooks/useAIPreferences';

interface SearchResultCardProps {
  hit: SearchHit;
  index: number;
  onViewDetails: (hit: SearchHit) => void;
}

export const SearchResultCard: React.FC<SearchResultCardProps> = ({
  hit,
  index,
  onViewDetails,
}) => {
  const { t } = useAIPreferences();
  const displayRank = hit.rank !== undefined && hit.rank !== null ? hit.rank : index + 1;

  const sourceTitle =
    hit.source_title ||
    (hit.source && typeof hit.source === 'object' && 'title' in hit.source
      ? String(hit.source.title)
      : null) ||
    'Tài liệu không có tiêu đề';

  const sourceUrl =
    hit.source_url ||
    (hit.source && typeof hit.source === 'object' && 'url' in hit.source
      ? String(hit.source.url)
      : null);

  const publisher =
    hit.publisher ||
    (hit.source && typeof hit.source === 'object' && 'publisher' in hit.source
      ? String(hit.source.publisher)
      : null);

  const pageNumber =
    hit.page_number !== undefined && hit.page_number !== null
      ? hit.page_number
      : hit.metadata?.page_number;

  return (
    <article
      className="search-result-card"
      data-testid={`search-result-card-${index}`}
      onClick={() => onViewDetails(hit)}
    >
      {/* Header: Rank + Source Title + Action */}
      <div className="card-top-row">
        <div className="card-identity-group">
          <span className="rank-badge" data-testid={`hit-rank-badge-${index}`}>
            #{displayRank}
          </span>
          <div className="card-title-meta">
            <h4 className="hit-source-title" data-testid={`hit-title-${index}`}>
              {sourceTitle}
            </h4>
            <div className="hit-provenance-line">
              {publisher && (
                <span className="hit-publisher" data-testid={`hit-publisher-${index}`}>
                  {publisher}
                </span>
              )}
              {pageNumber !== undefined && pageNumber !== null && (
                <span className="hit-page" data-testid={`hit-page-${index}`}>
                  Trang {pageNumber}
                </span>
              )}
              {sourceUrl && (
                <span
                  className="hit-url"
                  title={sourceUrl}
                  data-testid={`hit-url-${index}`}
                  onClick={(e) => e.stopPropagation()}
                >
                  <a href={sourceUrl} target="_blank" rel="noopener noreferrer">
                    {sourceUrl}
                  </a>
                </span>
              )}
            </div>
          </div>
        </div>

        {/* View Pipeline Button */}
        <button
          type="button"
          className="btn-inspect-pipeline"
          onClick={(e) => {
            e.stopPropagation();
            onViewDetails(hit);
          }}
          data-testid={`btn-view-details-${index}`}
          aria-label={`Xem chi tiết nguồn cho kết quả #${displayRank}`}
        >
<span>{t('search.technicalDetails')}</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>

      {/* Content passage snippet */}
      <p className="hit-content-passage" data-testid={`hit-content-${index}`}>
        {hit.content}
      </p>
    </article>
  );
};
