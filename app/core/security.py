"""
Security utilities for authentication and authorization.
Handles JWT tokens, password hashing, and user verification.
"""
from datetime import datetime, timedelta
from typing import Optional, Any
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security_scheme = HTTPBearer(auto_error=True)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str | uuid.UUID,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: User ID or identifier
        expires_delta: Token expiration time
        additional_claims: Extra data to include in token

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "iat": datetime.utcnow()
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def create_refresh_token(
    subject: str | uuid.UUID,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: User ID or identifier
        expires_delta: Token expiration time

    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.utcnow()
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> uuid.UUID:
    """
    Extract and validate user ID from JWT token.

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        User UUID

    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    payload = decode_token(token)

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type
    token_type = payload.get("type", "access")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Access token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current authenticated user from database.

    Args:
        user_id: User UUID from token
        db: Database session

    Returns:
        User model instance

    Raises:
        HTTPException: If user not found or inactive
    """
    # Import here to avoid circular dependency
    from app.models.user import User

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(
    current_user = Depends(get_current_user)
):
    """
    Ensure current user is active.
    Alias for get_current_user with explicit naming.
    """
    return current_user


def verify_refresh_token(token: str) -> uuid.UUID:
    """
    Verify a refresh token and extract user ID.

    Args:
        token: Refresh token string

    Returns:
        User UUID

    Raises:
        HTTPException: If token is invalid or not a refresh token
    """
    payload = decode_token(token)

    # Verify token type
    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Refresh token required.",
        )

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in refresh token",
        )

    return user_id
