"""Pydantic schemas for authentication, registration, and user profiles."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload schema for user registration."""

    email: EmailStr = Field(description="Unique email address for the user account")
    password: str = Field(min_length=6, max_length=128, description="Plaintext password")
    full_name: Optional[str] = Field(default=None, description="User full name (optional)")


class UserLoginRequest(BaseModel):
    """Payload schema for user login."""

    email: EmailStr = Field(description="Registered email address")
    password: str = Field(min_length=1, description="Account password")


class TokenResponse(BaseModel):
    """Response schema containing JWT access token and metadata."""

    access_token: str = Field(description="JWT bearer access token")
    token_type: str = Field(default="bearer", description="Token authentication scheme")
    expires_in: int = Field(description="Lifetime in seconds until expiration")


class UserResponse(BaseModel):
    """Sanitized user profile response schema (no password or sensitive fields)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Unique user identifier")
    email: str = Field(description="User email address")
    full_name: str = Field(description="User full name")
    role: str = Field(description="Assigned role: user, researcher, admin")
    is_active: bool = Field(description="Whether the user account is active")
    avatar_url: Optional[str] = Field(default=None, description="User avatar image data or URL")
    phone_number: Optional[str] = Field(default=None, description="Optional phone number")
    auth_provider: str = Field(default="local", description="Registration provider: local, google")
    created_at: datetime = Field(description="Account creation timestamp")


class UserProfileUpdate(BaseModel):
    """Editable fields for the authenticated user's profile."""

    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    phone_number: Optional[str] = Field(default=None, max_length=32)
    avatar_url: Optional[str] = Field(default=None, max_length=2_000_000)

class TokenPayload(BaseModel):
    """Internal decoded JWT token payload structure."""

    sub: str
    email: Optional[str] = None
    role: Optional[str] = "user"
    exp: Optional[int] = None


class GoogleUserInfo(BaseModel):
    """Parsed Google UserInfo payload from Google OpenID Connect."""

    sub: str = Field(description="Google subject unique identifier")
    email: EmailStr = Field(description="Google account primary email")
    name: Optional[str] = Field(default=None, description="Google profile display name")
    picture: Optional[str] = Field(default=None, description="Google profile picture URL")
    email_verified: bool = Field(default=False, description="Whether email is verified by Google")


class GoogleLoginResponse(BaseModel):
    """Response returned when initiating Google OAuth flow."""

    authorization_url: str = Field(description="Google OAuth consent authorization URL")
    state: str = Field(description="CSRF state token that must be verified in callback")
