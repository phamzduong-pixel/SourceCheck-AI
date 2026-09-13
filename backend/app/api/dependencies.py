"""FastAPI dependency injection providers."""

from typing import AsyncGenerator, Optional
from fastapi import Header, HTTPException, status
from app.core.database import get_db, check_db_connection
from app.services.embedding.embedding_service import EmbeddingService
from app.services.ingestion.ingestion_service import IngestionService
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.verification.verification_service import VerificationService

# Alias for backward compatibility
get_db_session = get_db


def get_embedding_service() -> EmbeddingService:
    """Provide EmbeddingService instance."""
    return EmbeddingService()


def get_ingestion_service() -> IngestionService:
    """Provide IngestionService instance."""
    return IngestionService()


def get_retrieval_service() -> RetrievalService:
    """Provide RetrievalService instance."""
    return RetrievalService()


def get_reranking_service():
    """Provide RerankingService instance."""
    from app.services.reranking.reranking_service import RerankingService
    return RerankingService()


def get_verification_service() -> VerificationService:
    """Provide VerificationService instance."""
    return VerificationService()


def get_qa_service():
    """Provide QAService instance."""
    from app.services.qa.qa_service import QAService
    return QAService()




def get_auth_service():
    """Provide AuthService instance."""
    from app.services.auth_service import AuthService
    return AuthService()


def get_google_oauth_provider():
    """Provide GoogleOAuthProvider instance."""
    from app.services.oauth.google import GoogleOAuthProvider
    return GoogleOAuthProvider()


from fastapi.security import OAuth2PasswordBearer
from uuid import UUID
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.core.config import settings
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Validate bearer access token and retrieve current user entity.
    
    Raises:
        HTTPException: 401 Unauthorized if token is missing, expired, or invalid.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa cung cấp thông tin xác thực (Bearer token required).",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không thể giải mã token xác thực.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Payload token không hợp lệ (thiếu sub).",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        user_uuid = UUID(str(user_id_str))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Định dạng user_id trong token không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    from app.services.auth_service import AuthService
    auth_service = AuthService()
    user = await auth_service.get_user_by_id(session, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy người dùng tương ứng với token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure currently authenticated user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản người dùng đã bị vô hiệu hóa.",
        )
    return current_user


async def verify_optional_token(
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """Skeleton dependency for optional bearer token verification."""
    if authorization and not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    return authorization
