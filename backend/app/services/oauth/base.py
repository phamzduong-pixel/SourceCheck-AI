"""Base OAuth provider abstraction."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseOAuthProvider(ABC):
    """Abstract base class for third-party OAuth providers."""

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Construct provider authorization URL embedding client_id, state, and scopes."""
        pass

    @abstractmethod
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens."""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Retrieve verified user profile from provider using access token."""
        pass
