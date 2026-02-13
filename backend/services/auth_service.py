"""Authentication service — login, register, token management."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password, verify_password, create_access_token, create_refresh_token
from core.utils import generate_slug
from db.models.organization import Organization
from db.models.user import User


class AuthService:
    """Handles authentication, registration, and token operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        organization_name: Optional[str] = None,
    ) -> tuple[User, Organization]:
        """Register a new user and optionally create an organization.

        Args:
            email: User email (must be unique)
            password: Plain text password (will be hashed)
            first_name: User's first name
            last_name: User's last name
            organization_name: If provided, creates a new org

        Returns:
            Tuple of (user, organization)

        Raises:
            ValueError: If email already exists
        """
        # Check for existing user
        existing = await self.db.execute(
            select(User).where(User.email == email, User.is_deleted == False)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Email already registered: {email}")

        # Create or find organization
        if organization_name:
            org = Organization(
                name=organization_name,
                slug=generate_slug(organization_name),
                subscription_plan="free",
            )
            self.db.add(org)
            await self.db.flush()
        else:
            # Default organization
            result = await self.db.execute(
                select(Organization).where(
                    Organization.slug == "default",
                    Organization.is_deleted == False,
                )
            )
            org = result.scalar_one_or_none()
            if not org:
                org = Organization(
                    name="Default Organization",
                    slug="default",
                    subscription_plan="free",
                )
                self.db.add(org)
                await self.db.flush()

        # Create user
        user = User(
            organization_id=org.id,
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        return user, org

    async def login(self, email: str, password: str) -> Optional[dict]:
        """Authenticate a user and return tokens.

        Args:
            email: User email
            password: Plain text password

        Returns:
            Dict with access_token, refresh_token, user info
            or None if authentication fails
        """
        result = await self.db.execute(
            select(User).where(
                User.email == email,
                User.is_deleted == False,
                User.is_active == True,
            )
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()

        # Generate tokens
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            org_id=user.organization_id,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            email=user.email,
            org_id=user.organization_id,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "organization_id": user.organization_id,
                "is_superadmin": user.is_superadmin,
            },
        }

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_deleted == False)
        )
        return result.scalar_one_or_none()
