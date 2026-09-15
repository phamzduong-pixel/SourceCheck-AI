"""Prompt templates for grounded generation in SourceCheck AI.

All prompts are strictly separated from service business logic.
"""

from typing import Optional


GROUNDED_QA_SYSTEM_PROMPT = """You are the Generation Engine of SourceCheck AI, a strict, factual, evidence-grounded fact-checking assistant.

Your task is to answer the user's question using ONLY the factual information provided in the [EVIDENCE] section below.

If [CONVERSATION_HISTORY] is provided, use it strictly as conversational context to understand the user's topic, follow-up intent, or pronoun references.
CRITICAL CONSTRAINT ON CONTEXT:
[CONVERSATION_HISTORY] is NOT evidence. You MUST NEVER treat conversational history as factual evidence or cite it. Every single fact, statistic, and statement in your answer MUST be directly supported by the [EVIDENCE] section.

STRICT CONSTRAINTS:
1. ONLY use information explicitly mentioned in the provided [EVIDENCE].
2. Do NOT use any pre-trained external knowledge, assumptions, or extrapolations.
3. If the provided [EVIDENCE] is empty, missing, irrelevant, or insufficient to answer the question, you MUST set status="INSUFFICIENT_EVIDENCE", answer="Thông tin trong các tài liệu kiểm chứng hiện tại không đủ để trả lời câu hỏi này.", and evidence_ids=[].
4. Do NOT hallucinate, guess, or synthesize facts beyond the text.
5. In evidence_ids, you MUST ONLY list the identifiers (e.g. "E1", "E2") of the evidence passages that directly support your statements. Do NOT invent new identifiers.
6. Always answer in Vietnamese unless the question explicitly asks for another language.
7. Return your response as a valid JSON object matching the required schema with keys: 'answer', 'status', 'evidence_ids'.
"""

GROUNDED_QA_USER_TEMPLATE = """[QUESTION]
{question}

[EVIDENCE]
{evidence_context}

Synthesize a precise, factual answer based strictly on the above evidence.
"""

GROUNDED_QA_USER_TEMPLATE_WITH_HISTORY = """[CONVERSATION_HISTORY]
{conversation_history}
[/CONVERSATION_HISTORY]

[QUESTION]
{question}

[EVIDENCE]
{evidence_context}

Synthesize a precise, factual answer based strictly on the above evidence.
"""


def render_grounded_qa_prompt(
    question: str,
    evidence_context: str,
    conversation_history: Optional[str] = None,
) -> str:
    """Render the user prompt injecting question, evidence block, and optional conversation history."""
    clean_evidence = evidence_context.strip() if evidence_context else "No evidence provided."
    clean_question = question.strip()

    if conversation_history and conversation_history.strip():
        return GROUNDED_QA_USER_TEMPLATE_WITH_HISTORY.format(
            conversation_history=conversation_history.strip(),
            question=clean_question,
            evidence_context=clean_evidence,
        )

    return GROUNDED_QA_USER_TEMPLATE.format(
        question=clean_question,
        evidence_context=clean_evidence,
    )
