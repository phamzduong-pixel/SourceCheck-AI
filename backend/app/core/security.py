"""Security, cryptography, and authentication utilities.

Provides password hashing via bcrypt, JWT issuance & decoding via PyJWT,
and data masking utilities for safe audit logging.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
import jwt

from app.core.config import settings


def get_password_hash(password: str) -> str:
    """Hash a plaintext password securely using bcrypt.
    
    Args:
        password: Raw plaintext password string.
        
    Returns:
        Salted bcrypt password hash string.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.
    
    Args:
        plain_password: Password string provided by client.
        hashed_password: Stored hash string from database.
        
    Returns:
        True if password matches hash, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create and sign a JWT access token with expiration.
    
    Args:
        data: Payload claims to embed in token (e.g. sub, email, role).
        expires_delta: Optional custom lifetime timedelta.
        
    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({
        "exp": expire,
        "iat": now,
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.effective_jwt_secret,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.
    
    Args:
        token: Encoded JWT string.
        
    Returns:
        Dict containing verified payload claims.
        
    Raises:
        jwt.PyJWTError: If token is expired, tampered, or invalid.
    """
    return jwt.decode(
        token,
        settings.effective_jwt_secret,
        algorithms=[settings.JWT_ALGORITHM],
    )


def verify_api_key(api_key: Optional[str]) -> bool:
    """Verify incoming client API key (placeholder for auth)."""
    if not api_key:
        return False
    return len(api_key) > 8


def mask_sensitive_data(text: str) -> str:
    """Mask sensitive tokens or keys for safe logging."""
    if not text or len(text) <= 8:
        return "***"
    return f"{text[:4]}...{text[-4:]}"
