"""Prompt templates for Claim Extraction and Claim Verification."""

from typing import List
from app.services.verification.schemas import MatchedEvidenceCandidate

# ---------------------------------------------------------------------------
# Claim Extraction Prompts
# ---------------------------------------------------------------------------

CLAIM_EXTRACTION_SYSTEM_PROMPT = """You are the Claim Extraction Engine of SourceCheck AI.

Your task is to decompose the provided text (an answer from an LLM) into atomic, independently verifiable factual claims.

RULES:
1. Each claim MUST be a single, standalone factual proposition that can be verified as true or false.
2. If a sentence contains multiple factual assertions, split them into separate atomic claims.
   Example:
   Input: "SIC đào tạo AI và IoT. Chương trình kéo dài 6 tháng."
   Output claims:
   - "SIC đào tạo AI."
   - "SIC đào tạo IoT."
   - "Chương trình kéo dài 6 tháng."
3. Preserve the exact factual meaning of the source text. Do NOT add outside knowledge, assumptions, or commentary.
4. Maintain the chronological order in which the facts appear in the text (order: 1, 2, 3...).
5. Ignore purely subjective opinions, greetings, polite filler words, or rhetorical questions.
6. Provide output strictly matching the JSON schema with a list of claims containing: 'claim_id' (e.g. "claim_1"), 'text' (the atomic proposition), 'order' (integer starting from 1).
"""

CLAIM_EXTRACTION_USER_TEMPLATE = """[ANSWER TO DECOMPOSE]
{answer}

Extract all atomic, verifiable factual claims in order.
"""


def render_claim_extraction_prompt(answer: str) -> str:
    """Render the user prompt for claim extraction."""
    return CLAIM_EXTRACTION_USER_TEMPLATE.format(answer=answer.strip())


# ---------------------------------------------------------------------------
# Claim Verification Prompts
# ---------------------------------------------------------------------------

CLAIM_VERIFICATION_SYSTEM_PROMPT = """You are the Claim Verification Judge of SourceCheck AI.

Your task is to evaluate a single factual CLAIM strictly against the provided [CANDIDATE EVIDENCES].

STRICT RULES:
1. Base your judgment ONLY on the provided [CANDIDATE EVIDENCES].
2. Do NOT use any pre-trained external knowledge, personal assumptions, or extrapolations.
3. Allowed verdicts:
   - "SUPPORTED": The evidence directly and sufficiently affirms the claim as factual truth.
   - "PARTIALLY_SUPPORTED": The evidence partially supports the claim, but minor numbers, scope, or conditions differ or are omitted.
   - "REFUTED": The evidence directly contradicts or disproves the claim.
   - "NOT_ENOUGH_INFO": The evidence does not contain sufficient information to determine whether the claim is true or false.
4. If you determine SUPPORTED, you MUST list the evidence IDs in 'supporting_evidence_ids'.
5. If you determine REFUTED, you MUST list the conflicting evidence IDs in 'refuting_evidence_ids'.
6. 'confidence': A float between 0.0 and 1.0 reflecting how certain the verification conclusion is given the evidence clarity. This represents verification certainty, NOT answer accuracy.
7. 'explanation': Provide a concise explanation citing the exact evidence ID (e.g. E1) and why it supports or refutes the claim.
8. Output MUST strictly conform to the required JSON schema.
"""

CLAIM_VERIFICATION_USER_TEMPLATE = """[CLAIM TO VERIFY]
Claim ID: {claim_id}
Claim Text: "{claim_text}"

[CANDIDATE EVIDENCES]
{evidences_text}

Evaluate the claim and output the structured verification result.
"""


def render_claim_verification_prompt(
    claim_id: str,
    claim_text: str,
    candidates: List[MatchedEvidenceCandidate],
) -> str:
    """Render user prompt for single claim verification with formatted candidate passages."""
    if not candidates:
        evidences_str = "No evidence passages provided."
    else:
        blocks = []
        for c in candidates:
            blocks.append(
                f"[{c.evidence_id}] Source: {c.source_title or 'Unknown'}\n"
                f"Content: \"{c.content}\""
            )
        evidences_str = "\n\n".join(blocks)

    return CLAIM_VERIFICATION_USER_TEMPLATE.format(
        claim_id=claim_id,
        claim_text=claim_text.strip(),
        evidences_text=evidences_str,
    )
