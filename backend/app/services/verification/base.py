"""Base abstraction for claim extraction implementations."""

from abc import ABC, abstractmethod
from typing import List, Optional
from app.services.verification.schemas import ClaimItem


class BaseClaimExtractor(ABC):
    """Abstract interface for claim extraction strategies (LLM-based, Rule-based)."""

    @abstractmethod
    async def extract_claims(
        self,
        answer: str,
        context: Optional[str] = None,
        max_claims: int = 20,
    ) -> List[ClaimItem]:
        """Extract atomic factual claims from answer text preserving sequence order."""
        pass
