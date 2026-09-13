"""Safety guardrail preventing jailbreaks and toxic inputs."""

from typing import Dict


class SafetyGuardrail:
    """Pre-execution security checks on user input."""

    BLOCKED_PATTERNS = ["ignore previous instructions", "system prompt reveal"]

    def validate_input(self, text: str) -> Dict[str, bool]:
        """Check for prompt injections or adversarial inputs."""
        lower = text.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in lower:
                return {"is_safe": False, "flagged_pattern": pattern}
        return {"is_safe": True, "flagged_pattern": None}
