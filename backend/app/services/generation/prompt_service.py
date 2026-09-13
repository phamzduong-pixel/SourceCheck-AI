"""Prompt template management and rendering for verification and reasoning."""

from typing import Any, Dict


class PromptService:
    """Manages prompt templates for fact extraction, entailment, and summarization."""

    CLAIM_EXTRACTION_SYSTEM = """You are an expert fact-checking assistant. Your task is to extract verifiable, factual claims from the text.
Do not extract subjective opinions, personal beliefs, or rhetorical questions.
Each claim must be independent and self-contained."""

    CLAIM_VERIFICATION_SYSTEM = """You are a rigorous fact-checking judge.
Given a factual claim and retrieved evidence passages, determine whether the evidence SUPPORTS, REFUTES, or does NOT PROVIDE ENOUGH INFO for the claim.
Always cite exact quotes and provide a step-by-step reasoning explanation."""

    CONTRADICTION_DETECTION_SYSTEM = """You are an investigative logic analyst.
Given multiple claims or multiple evidence snippets, detect any direct contradictions, logical inconsistencies, or conflicting numerical data."""

    def render_prompt(self, template: str, **kwargs: Any) -> str:
        """Format a prompt string with variables."""
        return template.format(**kwargs)
