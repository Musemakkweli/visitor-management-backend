
from datetime import datetime, timedelta, timezone

from jose import jwt
from pwdlib import PasswordHash

from app.config import settings


# Password hashing configuration
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password before saving it to the database."""
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """Check whether a password matches its stored hash."""
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
