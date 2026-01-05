import os
from datetime import datetime, timedelta, timezone
from typing import Optional, dict
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
# IMPORTANT: In Render, add a 'SECRET_KEY' environment variable for production security.
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-for-inawo")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- PASSWORD HASHING ---

def hash_password(password: str) -> str:
    """Hashes a plain text password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if a plain password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)

# --- JWT TOKEN MANAGEMENT ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a secure JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Standard JWT claim: 'exp' for expiration
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodes and validates a JWT token.
    Returns the payload if valid and not expired, otherwise None.
    """
    try:
        # jwt.decode automatically checks the 'exp' claim and raises JWTError if expired
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # Includes expired, invalid signature, or malformed tokens
        return None
