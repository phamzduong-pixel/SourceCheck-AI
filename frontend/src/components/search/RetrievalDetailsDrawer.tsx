/** A user-facing source details panel for a search result. */
import React, { useEffect } from 'react';
import { SearchHit } from '../../types/search';
import { useAIPreferences } from '../../hooks/useAIPreferences';

interface RetrievalDetailsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  hit: SearchHit | null;
  query?: string;
}

export const RetrievalDetailsDrawer: React.FC<RetrievalDetailsDrawerProps> = ({ isOpen, onClose, hit, query }) => {
  const { t } = useAIPreferences();
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !hit) return null;

  const sourceTitle = hit.source_title || (hit.source && typeof hit.source === 'object' && 'title' in hit.source ? String(hit.source.title) : null) || t('common.noTitle');
  const sourceUrl = hit.source_url || (hit.source && typeof hit.source === 'object' && 'url' in hit.source ? String(hit.source.url) : null);
  const publisher = hit.publisher || (hit.source && typeof hit.source === 'object' && 'publisher' in hit.source ? String(hit.source.publisher) : null);
  const pageNumber = hit.page_number ?? hit.metadata?.page_number;
  const documentId = hit.document_id || (hit.source && typeof hit.source === 'object' && 'document_id' in hit.source ? String(hit.source.document_id) : null);

  return (
    <>
      <div className="retrieval-drawer-backdrop" onClick={onClose} data-testid="retrieval-drawer-backdrop" />
      <aside className="retrieval-drawer" data-testid="retrieval-details-drawer">
        <div className="retrieval-drawer-header">
          <div className="drawer-title-group">
            {hit.rank !== undefined && hit.rank !== null && <span className="rank-badge primary" data-testid="drawer-hit-rank">#{hit.rank}</span>}
            <h3 className="drawer-title">{t('search.detailsTitle')}</h3>
          </div>
          <button type="button" className="drawer-close-btn" onClick={onClose} aria-label={t('common.closeDetails')} data-testid="btn-close-retrieval-drawer">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
        <div className="retrieval-drawer-content">
          {query && <div className="drawer-section"><div className="drawer-section-label">{t('search.query')}</div><div className="drawer-query-box" data-testid="drawer-query-box">"{query}"</div></div>}
          <div className="drawer-section">
            <div className="drawer-section-label">{t('search.chunkPassage')}</div>
            <div className="drawer-passage-box" data-testid="drawer-chunk-content">{hit.content}</div>
          </div>
          <div className="drawer-section">
            <div className="drawer-section-label">{t('search.sourceInfo')}</div>
            <div className="drawer-source-box">
              <div className="drawer-source-title" data-testid="drawer-source-title">{sourceTitle}</div>
              {sourceUrl && <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="drawer-source-link" data-testid="drawer-source-url">{sourceUrl}</a>}
            </div>
          </div>
          <div className="drawer-section">
            <div className="drawer-section-label">{t('search.metadata')}</div>
            <div className="drawer-meta-grid">
              {publisher && <div className="meta-item"><span className="meta-label">{t('common.source')}</span><span className="meta-value" data-testid="drawer-publisher">{publisher}</span></div>}
              {pageNumber !== undefined && pageNumber !== null && <div className="meta-item"><span className="meta-label">{t('common.page')}</span><span className="meta-value" data-testid="drawer-page-number">{t('common.page')} {pageNumber}</span></div>}
              {documentId && <div className="meta-item"><span className="meta-label">{t('common.document')}</span><span className="meta-value code-value" data-testid="drawer-document-id">{documentId}</span></div>}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};