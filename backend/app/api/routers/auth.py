"""Authentication API endpoints: registration, login, and user profile."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_auth_service,
    get_current_active_user,
    get_db,
    get_google_oauth_provider,
)
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import (
    GoogleLoginResponse,
    GoogleUserInfo,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService
from app.services.oauth.google import (
    GoogleOAuthProvider,
    generate_oauth_state,
    verify_oauth_state,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    request: UserRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):
    """Register a new user with email and password.
    
    - Validates email syntax.
    - Ensures email uniqueness (returns 400 Bad Request if already registered).
    - Hashes password using bcrypt.
    - Never stores or returns plaintext password.
    """
    user = await auth_service.register(session=db, request=request)
    user_resp = UserResponse.model_validate(user)
    return APIResponse(
        success=True,
        data=user_resp,
        message="Đăng ký tài khoản thành công.",
    )


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue JWT access token",
)
async def login(
    request: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate email and password, returning a signed JWT access token.
    
    - Verifies bcrypt hashed password.
    - Returns 401 Unauthorized for incorrect credentials.
    - Issues JWT containing `sub`, `email`, and `role` claims.
    """
    user = await auth_service.authenticate(session=db, request=request)
    
    # Generate JWT token
    token_claims = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
    }
    access_token = create_access_token(data=token_claims)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    token_resp = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
    )
    return APIResponse(
        success=True,
        data=token_resp,
        message="Đăng nhập thành công.",
    )


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve profile of the currently authenticated user",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """Return profile details for the authenticated user.
    
    - Requires valid Bearer JWT token in Authorization header.
    - Returns 401 Unauthorized if token is missing, invalid, or expired.
    - Never returns hashed_password.
    """
    user_resp = UserResponse.model_validate(current_user)
    return APIResponse(
        success=True,
        data=user_resp,
    )


@router.get(
    "/google/login",
    response_model=APIResponse[GoogleLoginResponse],
    summary="Initiate Google OAuth flow",
)
async def google_login(
    redirect: bool = False,
    google_provider: GoogleOAuthProvider = Depends(get_google_oauth_provider),
):
    """Initiate Google OAuth 2.0 OpenID Connect flow.
    
    - Generates signed, tamper-proof CSRF state token.
    - Constructs consent authorization URL.
    - If ?redirect=true: performs HTTP 307 temporary redirect.
    - Otherwise returns authorization URL and state in JSON response.
    """
    state = generate_oauth_state()
    auth_url = google_provider.get_authorization_url(state=state)

    if redirect:
        return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    return APIResponse(
        success=True,
        data=GoogleLoginResponse(authorization_url=auth_url, state=state),
        message="Khởi tạo luồng xác thực Google OAuth thành công.",
    )


@router.get(
    "/google/callback",
    response_model=APIResponse[TokenResponse],
    summary="Handle Google OAuth callback and issue SourceCheck JWT",
)
async def google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    google_provider: GoogleOAuthProvider = Depends(get_google_oauth_provider),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):
    """Callback endpoint for Google OAuth authorization code exchange.
    
    - Validates state parameter to mitigate CSRF attacks.
    - Exchanges code for Google access token.
    - Fetches user identity from Google userinfo endpoint.
    - Authenticates or safely links/creates SourceCheck user.
    - Issues SourceCheck JWT access token.
    """
    if error:
        logger.warning(f"Google OAuth returned error in callback: {error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth xác thực thất bại: {error}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu tham số mã ủy quyền (code) hoặc state từ Google.",
        )

    if not verify_oauth_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State token không hợp lệ hoặc đã hết hạn (CSRF validation failed).",
        )

    # Exchange code for Google tokens
    token_data = await google_provider.exchange_code_for_token(code)
    google_access_token = token_data.get("access_token")
    if not google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google không trả về access_token hợp lệ.",
        )

    # Retrieve user info from Google
    user_info_raw = await google_provider.get_user_info(google_access_token)
    google_user = GoogleUserInfo(
        sub=str(user_info_raw.get("sub")),
        email=user_info_raw.get("email"),
        name=user_info_raw.get("name"),
        picture=user_info_raw.get("picture"),
        email_verified=bool(user_info_raw.get("email_verified", False)),
    )

    # Authenticate or safely link/create user
    user = await auth_service.authenticate_or_create_google_user(
        session=db,
        google_user=google_user,
    )

    # Issue SourceCheck JWT
    token_claims = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
    }
    access_token = create_access_token(data=token_claims)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return APIResponse(
        success=True,
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
        ),
        message="Đăng nhập Google thành công.",
    )
