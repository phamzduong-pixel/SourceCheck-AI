"""Google OAuth 2.0 / OpenID Connect provider implementation."""

import logging
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from fastapi import HTTPException, status
import httpx
import jwt

from app.core.config import settings
from app.services.oauth.base import BaseOAuthProvider

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def generate_oauth_state() -> str:
    """Generate a tamper-proof, signed OAuth CSRF state token with 10-minute expiration."""
    now = datetime.now(timezone.utc)
    payload = {
        "nonce": secrets.token_urlsafe(16),
        "type": "oauth_state",
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    return jwt.encode(
        payload,
        settings.effective_jwt_secret,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_oauth_state(state: str) -> bool:
    """Validate incoming OAuth state token against expiration and signature.
    
    Args:
        state: Encoded JWT state string.
        
    Returns:
        True if valid and unexpired, False otherwise.
    """
    if not state:
        return False
    try:
        decoded = jwt.decode(
            state,
            settings.effective_jwt_secret,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return decoded.get("type") == "oauth_state"
    except Exception as exc:
        logger.warning(f"OAuth state verification failed: {exc}")
        return False


class GoogleOAuthProvider(BaseOAuthProvider):
    """Google OAuth 2.0 provider implementing authorization, token exchange, and profile fetch."""

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        redirect_uri: str = "",
    ):
        self.client_id = client_id or settings.GOOGLE_CLIENT_ID
        self.client_secret = client_secret or settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

    def get_authorization_url(self, state: str) -> str:
        """Construct the Google OAuth consent authorization URL."""
        if not self.client_id:
            logger.warning("GOOGLE_CLIENT_ID is not configured in settings.")

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code with Google token endpoint for access token.
        
        Raises:
            HTTPException: 400 Bad Request if token exchange fails.
        """
        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(GOOGLE_TOKEN_URL, data=payload)
                if response.status_code != 200:
                    logger.error(f"Google token exchange failed: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Không thể trao đổi mã xác thực với máy chủ Google.",
                    )
                return response.json()
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(f"Network error during Google token exchange: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Lỗi kết nối tới máy chủ Google OAuth.",
            )

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Retrieve verified user profile from Google userinfo endpoint.
        
        Raises:
            HTTPException: 400 Bad Request if userinfo request fails.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
                if response.status_code != 200:
                    logger.error(f"Google userinfo failed: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Không thể truy xuất thông tin người dùng từ Google.",
                    )
                return response.json()
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(f"Network error during Google userinfo retrieval: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Lỗi kết nối khi lấy thông tin tài khoản Google.",
            )
