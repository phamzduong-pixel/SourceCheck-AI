/**
 * AnswerRenderer: Parses synthesized answer text, transforming footnote citation tags
 * (e.g. [1], [2]) into interactive, accessible clickable badges that trigger the Evidence Drawer.
 */

import React from 'react';
import { CitationItem } from '../../types/qa';

interface AnswerRendererProps {
  answerText: string;
  citations: CitationItem[];
  onCitationClick: (citation: CitationItem) => void;
  showCitations?: boolean;
}

export const AnswerRenderer: React.FC<AnswerRendererProps> = ({
  answerText,
  citations,
  onCitationClick,
  showCitations = true,
}) => {
  if (!answerText) {
    return null;
  }

  if (!showCitations) {
    return (
      <div className="answer-body" data-testid="answer-rendered-text">
        {answerText.replace(/\[\d+\]/g, '').replace(/\s{2,}/g, ' ').trim()}
      </div>
    );
  }

  // Create lookup map from footnote_index to CitationItem
  const citationMap = new Map<number, CitationItem>();
  citations.forEach((cit) => {
    if (typeof cit.footnote_index === 'number') {
      citationMap.set(cit.footnote_index, cit);
    }
  });

  // Regex pattern matching tags like [1], [2], [10]
  const pattern = /\[(\d+)\]/g;
  const elements: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(answerText)) !== null) {
    const matchIndex = match.index;
    const fullMatch = match[0]; // e.g. "[1]"
    const footnoteNum = parseInt(match[1], 10);

    // Push preceding text segment
    if (matchIndex > lastIndex) {
      elements.push(answerText.slice(lastIndex, matchIndex));
    }

    const citation = citationMap.get(footnoteNum);

    if (citation) {
      elements.push(
        <button
          key={`cit-${footnoteNum}-${matchIndex}`}
          type="button"
          className="citation-pill"
          onClick={() => onCitationClick(citation)}
          aria-label={`Xem bằng chứng số [${footnoteNum}]`}
          data-testid={`citation-btn-${footnoteNum}`}
        >
          {fullMatch}
        </button>
      );
    } else {
      // If footnote number not found in citations array, preserve as plain text
      elements.push(
        <span key={`plain-${footnoteNum}-${matchIndex}`} className="citation-pill">
          {fullMatch}
        </span>
      );
    }

    lastIndex = pattern.lastIndex;
  }

  // Push remaining trailing text
  if (lastIndex < answerText.length) {
    elements.push(answerText.slice(lastIndex));
  }

  return (
    <div className="answer-body" data-testid="answer-rendered-text">
      {elements}
    </div>
  );
};