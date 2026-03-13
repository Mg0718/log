from __future__ import annotations

import os
import time
from typing import Optional

import bcrypt
from jose import JWTError, jwt

# Secret key — override via JWT_SECRET env var in production
SECRET_KEY = os.getenv("JWT_SECRET", "logosgotham-dev-secret-2026-hackathon-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24  # 24 hours


def _hash(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def _verify(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)


# Demo users for the prototype.
# Roles align with the layered design: admin, seller, receiver.
# Keep `buyer` as a backward-compatible alias that maps to receiver role.
_DEMO_USERS: dict[str, dict] = {
    "admin": {
        "username": "admin",
        "role": "admin",
        "full_name": "Ops Control (Admin)",
        "hashed_password": _hash("admin123"),
    },
    "seller": {
        "username": "seller",
        "role": "seller",
        "full_name": "Alice (Seller)",
        "hashed_password": _hash("seller123"),
    },
    "receiver": {
        "username": "receiver",
        "role": "receiver",
        "full_name": "Bob (Receiver)",
        "hashed_password": _hash("receiver123"),
    },
    "buyer": {
        "username": "buyer",
        "role": "receiver",
        "full_name": "Bob (Receiver)",
        "hashed_password": _hash("buyer123"),
    },
}


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Return user dict if credentials are valid, else None."""
    user = _DEMO_USERS.get(username)
    if not user:
        return None
    if not _verify(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict) -> str:
    """Encode a signed JWT with 24-hour expiry."""
    to_encode = data.copy()
    to_encode["exp"] = int(time.time()) + ACCESS_TOKEN_EXPIRE_SECONDS
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT. Returns payload dict or None if invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except JWTError:
        return None
