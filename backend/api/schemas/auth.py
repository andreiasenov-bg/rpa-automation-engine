"""Authentication schemas."""

from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import List, Optional


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr = Field(description="User email address")
    password: str = Field(min_length=1, description="User password")


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(description="User email address")
    password: str = Field(min_length=8, description="User password (min 8 characters)")
    first_name: str = Field(min_length=1, description="User first name")
    last_name: str = Field(min_length=1, description="User last name")
    org_name: str = Field(min_length=1, description="Organization name")


class TokenResponse(BaseModel):
    """Token response with access and refresh tokens."""

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(description="Refresh token to exchange for new access token")


class UserResponse(BaseModel):
    """User information response."""

    id: str = Field(description="User ID")
    email: str = Field(description="User email address")
    first_name: str = Field(description="User first name")
    last_name: str = Field(description="User last name")
    org_id: str = Field(description="Organization ID")
    is_active: bool = Field(description="Whether user account is active")
    roles: List[str] = Field(default=[], description="User roles")
    created_at: datetime = Field(description="User creation timestamp")

    class Config:
        from_attributes = True
