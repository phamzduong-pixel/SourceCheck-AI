"""Authentication service managing user registration, credential verification, and profile retrieval."""

import logging
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import (
    GoogleUserInfo,
    UserLoginRequest,
    UserRegisterRequest,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Service handling user account registration and authentication logic."""

    async def register(
        self,
        session: AsyncSession,
        request: UserRegisterRequest,
    ) -> User:
        """Register a new user account with unique email and hashed password.
        
        Args:
            session: Async database session.
            request: Validated registration payload.
            
        Returns:
            Newly created User model entity.
            
        Raises:
            HTTPException: 400 Bad Request if email is already taken.
        """
        clean_email = str(request.email).lower().strip()
        
        # Check if email is already registered
        stmt = select(User).where(User.email == clean_email)
        result = await session.execute(stmt)
        existing_user = result.scalars().first()
        if existing_user:
            logger.warning(f"Registration attempt with duplicate email: {clean_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email đã được đăng ký trong hệ thống.",
            )
            
        # Hash password securely using bcrypt
        hashed = get_password_hash(request.password)
        
        # Fallback full_name to email username if not explicitly provided
        full_name = (
            request.full_name.strip()
            if request.full_name and request.full_name.strip()
            else clean_email.split("@")[0]
        )
        
        new_user = User(
            email=clean_email,
            hashed_password=hashed,
            full_name=full_name,
            role="user",
            is_active=True,
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        logger.info(f"User registered successfully: id={new_user.id}, email={new_user.email}")
        return new_user

    async def authenticate(
        self,
        session: AsyncSession,
        request: UserLoginRequest,
    ) -> User:
        """Verify user credentials and return active user entity.
        
        Args:
            session: Async database session.
            request: Login request containing email and password.
            
        Returns:
            Authenticated User entity.
            
        Raises:
            HTTPException: 401 Unauthorized for bad credentials,
                           400 Bad Request for inactive accounts.
        """
        clean_email = str(request.email).lower().strip()
        stmt = select(User).where(User.email == clean_email)
        result = await session.execute(stmt)
        user = result.scalars().first()
        
        if not user or not verify_password(request.password, user.hashed_password):
            logger.warning(f"Failed authentication attempt for email: {clean_email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không chính xác.",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not user.is_active:
            logger.warning(f"Authentication attempt on inactive account: {clean_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tài khoản người dùng đã bị vô hiệu hóa.",
            )
            
        logger.info(f"User authenticated successfully: id={user.id}, email={user.email}")
        return user

    async def get_user_by_id(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> Optional[User]:
        """Fetch user by primary key UUID."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_user_by_email(
        self,
        session: AsyncSession,
        email: str,
    ) -> Optional[User]:
        """Fetch user by email."""
        clean_email = email.lower().strip()
        stmt = select(User).where(User.email == clean_email)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def authenticate_or_create_google_user(
        self,
        session: AsyncSession,
        google_user: GoogleUserInfo,
    ) -> User:
        """Authenticate an existing Google user or safely register/link a new one.
        
        Args:
            session: Async database session.
            google_user: Validated Google user profile.
            
        Returns:
            Authenticated User entity.
            
        Raises:
            HTTPException: 400 if Google email is unverified,
                           409 if email is already linked to a different Google account.
        """
        # 1. Lookup by Google Subject ID
        stmt_google = select(User).where(User.google_id == google_user.sub)
        res_google = await session.execute(stmt_google)
        existing_google_user = res_google.scalars().first()

        if existing_google_user:
            if not existing_google_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tài khoản người dùng đã bị vô hiệu hóa.",
                )
            # Update profile info if changed
            updated = False
            if google_user.picture and existing_google_user.avatar_url != google_user.picture:
                existing_google_user.avatar_url = google_user.picture
                updated = True
            if google_user.name and not existing_google_user.full_name:
                existing_google_user.full_name = google_user.name
                updated = True
            if updated:
                await session.commit()
                await session.refresh(existing_google_user)
            logger.info(f"Existing Google user authenticated: id={existing_google_user.id}")
            return existing_google_user

        # 2. Lookup by email for safe account linking
        clean_email = str(google_user.email).lower().strip()
        stmt_email = select(User).where(User.email == clean_email)
        res_email = await session.execute(stmt_email)
        existing_email_user = res_email.scalars().first()

        if existing_email_user:
            if not existing_email_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tài khoản người dùng đã bị vô hiệu hóa.",
                )
            # Safe linking check: only link if email is verified by Google
            if not google_user.email_verified:
                logger.warning(f"Rejecting unverified Google email linking for {clean_email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email tài khoản Google chưa được xác thực, không thể liên kết tài khoản.",
                )
            # Check for conflict: if already linked to a different google_id
            if existing_email_user.google_id and existing_email_user.google_id != google_user.sub:
                logger.warning(f"Conflicting Google account linking for {clean_email}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email này đã được liên kết với một tài khoản Google khác.",
                )

            # Safely associate Google ID with existing local user
            existing_email_user.google_id = google_user.sub
            if google_user.picture and not existing_email_user.avatar_url:
                existing_email_user.avatar_url = google_user.picture
            await session.commit()
            await session.refresh(existing_email_user)
            logger.info(f"Safely linked Google account to existing user: id={existing_email_user.id}")
            return existing_email_user

        # 3. Create new user account via Google OAuth
        full_name = (
            google_user.name.strip()
            if google_user.name and google_user.name.strip()
            else clean_email.split("@")[0]
        )
        new_user = User(
            email=clean_email,
            hashed_password=None,
            full_name=full_name,
            role="user",
            is_active=True,
            google_id=google_user.sub,
            avatar_url=google_user.picture,
            auth_provider="google",
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        logger.info(f"Created new user via Google OAuth: id={new_user.id}, email={new_user.email}")
        return new_user
