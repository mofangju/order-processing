"""Authentication and authorization utilities."""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import settings

bearer = HTTPBearer()


def create_access_token(subject: str) -> str:
    """
    Create a JWT access token for a user.

    Args:
        subject: User identifier to encode in the token

    Returns:
        Encoded JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expires_minutes
    )
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(
        to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> str:
    """
    Extract and validate the current user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User ID from the token

    Raises:
        HTTPException: If token is invalid or missing user ID
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        return user_id
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
        ) from e
