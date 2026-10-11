import hashlib
import hmac
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.core.config import settings

def hash_password(password: str) -> str:
    """Hash passwords with a unique random salt and PBKDF2."""
    salt = secrets.token_bytes(16)
    pwd_bytes = password.encode('utf-8')
    iterations = 310_000
    hashed = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${hashed.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify new hashes and legacy hashes during migration."""
    try:
        algorithm, iterations, salt, expected = hashed_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        # Older accounts used a shared JWT-derived salt. Continue to accept them
        # so a successful login can migrate the stored hash.
        legacy_salt = settings.JWT_SECRET[:16].encode("utf-8")
        legacy_hash = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), legacy_salt, 100_000
        ).hex()
        return hmac.compare_digest(legacy_hash, hashed_password or "")

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with payload data and expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
