import React from 'react';
import { VerificationResultResponse } from '../../types/verification';

interface VerificationResultCardProps {
  report: VerificationResultResponse;
}

/** Renders the persisted verification report returned by /verify/{request_id}. */
export const VerificationResultCard: React.FC<VerificationResultCardProps> = ({ report }) => (
  <section className="verification-result-card" data-testid="verification-result-card">
    <div className="verification-result-header">
      <div>
        <h3>Verification Result</h3>
        {report.summary && <p>{report.summary}</p>}
      </div>
      <span className={`claim-verdict-pill ${report.overall_verdict.toLowerCase()}`}>
        {report.overall_verdict}
      </span>
    </div>

    <div className="verification-result-claims">
      {report.claims.map((claim, index) => (
        <article key={claim.claim_id || `${claim.claim_text}-${index}`} className="verification-result-claim" data-testid={`verification-claim-${index}`}>
          <div className="verification-claim-heading">
            <span className="claim-order-badge">#{index + 1}</span>
            <p>{claim.claim_text}</p>
            <span className={`claim-verdict-pill ${claim.verdict.toLowerCase()}`}>{claim.verdict}</span>
          </div>
          {claim.explanation && <p className="claim-explanation">{claim.explanation}</p>}
          {claim.evidences.length > 0 ? (
            <div className="verification-evidence-list">
              {claim.evidences.map((evidence, evidenceIndex) => (
                <div key={`${evidence.evidence_id || evidence.source_title}-${evidenceIndex}`} className="verification-evidence">
                  <span className={`stance-tag ${evidence.stance.toLowerCase()}`}>{evidence.stance}</span>
                  {evidence.source_url ? <a href={evidence.source_url} target="_blank" rel="noreferrer">{evidence.source_title}</a> : <strong>{evidence.source_title}</strong>}
                  <blockquote>{evidence.quote || evidence.snippet}</blockquote>
                </div>
              ))}
            </div>
          ) : <p className="claim-no-evidence">Chưa có bằng chứng liên kết</p>}
        </article>
      ))}
    </div>
  </section>
);