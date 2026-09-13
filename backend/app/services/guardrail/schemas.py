"""Schemas for Input and Output Guardrail checks."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GuardrailStatus(str, Enum):
    """Status resulting from guardrail checks."""

    PASSED = "PASSED"
    BLOCKED = "BLOCKED"
    FLAGGED = "FLAGGED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class InputValidationResult(BaseModel):
    """Result of validating a user input question."""

    is_valid: bool = Field(..., description="True if input passes all guardrails and is safe to execute")
    status: GuardrailStatus = Field(..., description="PASSED, BLOCKED, or FLAGGED")
    flagged_reasons: List[str] = Field(default_factory=list, description="Reasons for rejection or flagging")
    sanitized_input: str = Field(..., description="Sanitized version of user question")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OutputValidationResult(BaseModel):
    """Result of validating an assembled final response before returning to user."""

    is_valid: bool = Field(..., description="True if output satisfies all grounding, verification, and citation rules")
    status: GuardrailStatus = Field(..., description="PASSED, BLOCKED, or INSUFFICIENT_EVIDENCE")
    violations: List[str] = Field(default_factory=list, description="List of detected policy or integrity violations")
    metadata: Dict[str, Any] = Field(default_factory=dict)
