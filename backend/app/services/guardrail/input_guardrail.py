"""Input Guardrail service preventing malicious prompts, empty/oversized inputs, and handling untrusted documents."""

import logging
import re
from typing import List, Optional
from app.services.guardrail.schemas import GuardrailStatus, InputValidationResult

logger = logging.getLogger(__name__)


class InputGuardrail:
    """Validates user queries and sanitizes untrusted document content."""

    # Explicit list of prompt injection and instruction hijack patterns (case-insensitive regex)
    PROMPT_INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous\s+)?instructions",
        r"disregard\s+(all\s+)?(previous\s+)?instructions",
        r"system\s+prompt(\s+reveal)?",
        r"reveal\s+(the\s+)?(system\s+)?prompt",
        r"print\s+(the\s+)?(system\s+)?prompt",
        r"forget\s+(all\s+)?(your\s+)?instructions",
        r"override\s+(all\s+)?(system\s+)?rules",
        r"bypass\s+(all\s+)?guardrails",
        r"\bdan\s+mode\b",
        r"\bjailbreak\b",
        r"\bdeveloper\s+mode\b",
        r"act\s+as\s+(an?\s+)?unrestricted",
        r"you\s+are\s+now\s+(an?\s+)?unrestricted",
        r"repeat\s+everything\s+above",
        r"output\s+the\s+exact\s+system\s+instructions",
    ]

    def __init__(self, max_question_length: int = 2000):
        self.max_question_length = max_question_length
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.PROMPT_INJECTION_PATTERNS
        ]

    def validate_question(self, question: Optional[str]) -> InputValidationResult:
        """Validate user query for emptiness, excessive length, and prompt injection attacks.
        
        Args:
            question: Raw user question string.
            
        Returns:
            InputValidationResult with safety flag, status, and detected reasons.
        """
        # 1. Check for empty or whitespace-only question
        if not question or not question.strip():
            logger.warning("InputGuardrail rejected: empty or whitespace-only question.")
            return InputValidationResult(
                is_valid=False,
                status=GuardrailStatus.BLOCKED,
                flagged_reasons=["Empty or whitespace question"],
                sanitized_input="",
                metadata={"length": 0},
            )

        trimmed = question.strip()

        # 2. Check maximum question length
        if len(trimmed) > self.max_question_length:
            logger.warning(
                f"InputGuardrail rejected: query length {len(trimmed)} exceeds max limit {self.max_question_length}."
            )
            return InputValidationResult(
                is_valid=False,
                status=GuardrailStatus.BLOCKED,
                flagged_reasons=[
                    f"Question length ({len(trimmed)}) exceeds maximum character limit of {self.max_question_length}"
                ],
                sanitized_input=trimmed[: self.max_question_length],
                metadata={"length": len(trimmed), "max_allowed": self.max_question_length},
            )

        # 3. Detect prompt injection / jailbreak patterns
        flagged_patterns: List[str] = []
        for compiled in self._compiled_patterns:
            if compiled.search(trimmed):
                flagged_patterns.append(compiled.pattern)

        if flagged_patterns:
            logger.warning(
                f"InputGuardrail detected prompt injection patterns: {flagged_patterns}"
            )
            return InputValidationResult(
                is_valid=False,
                status=GuardrailStatus.BLOCKED,
                flagged_reasons=[
                    f"Detected prompt injection or adversarial pattern: '{p}'"
                    for p in flagged_patterns
                ],
                sanitized_input=trimmed,
                metadata={"detected_patterns": flagged_patterns},
            )

        # 4. Valid input
        return InputValidationResult(
            is_valid=True,
            status=GuardrailStatus.PASSED,
            flagged_reasons=[],
            sanitized_input=trimmed,
            metadata={"length": len(trimmed)},
        )

    def sanitize_untrusted_content(self, text: str) -> str:
        """Sanitize untrusted content retrieved from documents or evidence.
        
        Treats document/evidence text as untrusted passive data:
        - Prevents prompt injection instructions inside ingested documents from being
          executed as system instructions by prefixing or tagging them cleanly.
        """
        if not text:
            return ""

        # Normalize control characters and escape potential delimiter clashes
        sanitized = text.replace("\x00", "")
        
        # Ensure that instruction-hijack markers in documents are neutralized
        # (e.g. replacing direct 'System:' or 'Instruction:' role tags)
        neutralized = re.sub(r"(?i)\b(system|developer|instruction)\s*:", r"[untrusted_\1_tag]", sanitized)
        return neutralized


    def wrap_evidence_safely(self, evidence_id: str, content: str, source: str = "") -> str:
        """Encapsulate evidence in a strictly passive data block to isolate untrusted text."""
        safe_content = self.sanitize_untrusted_content(content)
        return (
            f"<evidence_data id=\"{evidence_id}\" source=\"{source}\">\n"
            f"{safe_content}\n"
            f"</evidence_data>"
        )
