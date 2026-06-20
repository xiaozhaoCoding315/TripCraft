"""
TripCraft Authentication Service

Provides JWT-based authentication for API endpoints.
Passwords are hashed using SHA-256 with salt.
Tokens expire after 24 hours by default.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import Settings, get_settings

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


class User:
    """Simple user model for authentication"""

    def __init__(self, user_id: str, username: str, email: Optional[str] = None):
        self.user_id = user_id
        self.username = username
        self.email = email

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
        }


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with random salt"""
    salt = secrets.token_hex(16)
    hash_value = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${hash_value}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt, stored_hash = hashed_password.split("$")
        computed_hash = hashlib.sha256(f"{salt}{plain_password}".encode()).hexdigest()
        return secrets.compare_digest(computed_hash, stored_hash)
    except (ValueError, AttributeError):
        return False


def create_access_token(
    user_id: str,
    username: str,
    settings: Settings,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token"""
    if expires_delta is None:
        expires_delta = timedelta(hours=24)

    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": user_id,
        "username": username,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }

    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str, settings: Settings) -> dict:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings: Settings = Depends(get_settings),
) -> Optional[User]:
    """
    Dependency to extract current user from JWT token.
    Returns None if no token is provided (optional auth).
    """
    if credentials is None:
        return None

    payload = decode_token(credentials.credentials, settings)
    user_id = payload.get("sub")
    username = payload.get("username")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return User(user_id=user_id, username=username)


async def require_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Dependency that requires authentication.
    Raises 401 if no valid token is provided.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def generate_api_key() -> str:
    """Generate a random API key for user registration"""
    import secrets
    return f"tc_{secrets.token_urlsafe(32)}"
