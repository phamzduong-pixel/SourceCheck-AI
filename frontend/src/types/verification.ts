/**
 * Fact-Checking Verification schemas matching backend app.schemas.verification and app.schemas.claim.
 *
 * NOTE: In this endpoint (/verify), stance is located directly inside VerificationEvidenceItem.
 */

export type VerificationVerdict =
  | 'SUPPORTED'
  | 'REFUTED'
  | 'PARTIALLY_SUPPORTED'
  | 'NOT_ENOUGH_INFO'
  | string;

export type OverallVerdict = 'TRUE' | 'FALSE' | 'MIXED' | 'UNVERIFIED' | string;

export type VerificationStance = 'SUPPORTS' | 'REFUTES' | 'NEUTRAL' | string;

export interface ClaimExtractRequest {
  text: string;
  max_claims?: number;
}

export interface ExtractedClaim {
  claim_id?: string | null;
  claim_text: string;
  context_sentence?: string | null;
  verifiable?: boolean;
}

export interface ClaimExtractResponse {
  total_claims: number;
  claims: ExtractedClaim[];
}

export interface VerificationEvidenceItem {
  evidence_id?: string | null;
  source_title: string;
  source_url?: string | null;
  publisher?: string | null;
  snippet: string;
  stance: VerificationStance;
  quote?: string | null;
  relevance_score: number;
}

export interface VerifiedClaimItem {
  claim_id?: string | null;
  claim_text: string;
  verdict: VerificationVerdict;
  confidence_score: number;
  explanation?: string | null;
  evidences: VerificationEvidenceItem[];
}

export interface VerificationCreateRequest {
  text: string;
  source_url?: string | null;
  enable_contradiction_check?: boolean;
  top_k_evidence?: number;
}

export interface VerificationResultResponse {
  request_id: string;
  status: string;
  overall_verdict: OverallVerdict;
  summary?: string | null;
  claims_count: number;
  claims: VerifiedClaimItem[];
  created_at: string;
  completed_at?: string | null;
}
