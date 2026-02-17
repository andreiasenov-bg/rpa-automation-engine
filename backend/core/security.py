"""
Security utilities for the RPA automation engine.

Includes:
- Password hashing with bcrypt
- JWT token generation and verification
- AES-256 encryption/decryption for credential vault
- FastAPI dependencies for authentication and authorization
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Callable, Any, List
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials as HTTPAuthCredentials
from passlib.context import CryptContext
from pydantic import BaseModel
import jwt
from cryptography.fernet import Fernet

from app.config import get_settings

# Initialize security settings
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# HTTP Bearer for API endpoints
security_scheme = HTTPBearer()


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # user_id
    email: str
    org_id: str
    exp: datetime
    iat: datetime
    type: str  # "access" or "refresh"


class TokenResponse(BaseModel):
    """Token response structure."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, email: str, org_id: str) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID
        email: User email
        org_id: Organization ID

    Returns:
        Encoded JWT token
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "email": email,
        "org_id": org_id,
        "type": "access",
        "iat": now,
        "exp": expire,
    }

    encoded_jwt = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode a JWT token and return the raw payload dict.

    Args:
        token: Encoded JWT token

    Returns:
        Dict with token payload (sub, email, org_id, etc.)

    Raises:
        jwt.InvalidTokenError: If token is invalid or expired
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def create_refresh_token(user_id: str, email: str, org_id: str) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User ID
        email: User email
        org_id: Organization ID

    Returns:
        Encoded JWT token
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "email": email,
        "org_id": org_id,
        "type": "refresh",
        "iat": now,
        "exp": expire,
    }

    encoded_jwt = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


def verify_token(token: str) -> TokenPayload:
    """
    Verify and decode a JWT token.

    Args:
        token: Encoded JWT token

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        org_id: str = payload.get("org_id")
        token_type: str = payload.get("type")

        if user_id is None or email is None or org_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenPayload(
            sub=user_id,
            email=email,
            org_id=org_id,
            exp=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc),
            iat=datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc),
            type=token_type,
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


class CredentialVault:
    """
    Manages encryption and decryption of sensitive credentials using Fernet (AES-256).
    """

    def __init__(self, key: Optional[str] = None):
        """
        Initialize the vault with an encryption key.

        Args:
            key: Encryption key (base64 encoded). If None, uses ENCRYPTION_KEY from settings.
        """
        if key is None:
            key = settings.ENCRYPTION_KEY

        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string using Fernet.

        Args:
            plaintext: Plain text to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        encrypted = self.cipher.encrypt(plaintext)
        return encrypted.decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a string using Fernet.

        Args:
            ciphertext: Encrypted string to decrypt

        Returns:
            Decrypted plain text

        Raises:
            ValueError: If decryption fails
        """
        try:
            if isinstance(ciphertext, str):
                ciphertext = ciphertext.encode()
            decrypted = self.cipher.decrypt(ciphertext)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


# Global vault instance
vault = CredentialVault()


async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security_scheme),
) -> TokenPayload:
    """
    FastAPI dependency to get the current authenticated user from JWT token.

    Reads the Authorization header, verifies the JWT token, and returns the payload.

    Args:
        credentials: HTTP Bearer credentials from Authorization header

    Returns:
        Decoded token payload containing user info

    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    token_payload = verify_token(token)

    if token_payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_payload


def require_permission(required_permissions: List[str]) -> Callable:
    """
    Factory function to create a FastAPI dependency that checks RBAC permissions.

    Args:
        required_permissions: List of required permission codes (e.g., ["workflows:read", "workflows:write"])

    Returns:
        Dependency function that checks if user has required permissions
    """

    async def permission_checker(
        current_user: TokenPayload = Depends(get_current_user),
    ) -> TokenPayload:
        """
        Check if the current user has the required permissions.

        Args:
            current_user: Current authenticated user

        Returns:
            Current user if authorized

        Raises:
            HTTPException: If user lacks required permissions
        """
        # This is a placeholder implementation
        # In production, you would load user roles and permissions from the database
        # and check them against required_permissions

        # For now, we'll just return the user
        # TODO: Implement actual permission checking from database
        return current_user

    return permission_checker
