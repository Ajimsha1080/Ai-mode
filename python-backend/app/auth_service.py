import os
import time
import uuid
import jwt
import bcrypt
import logging
from typing import Dict, Any, Optional, Tuple
from collections import defaultdict
from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger("shopmate_auth")

SESSION_JWT_SECRET = os.getenv("SESSION_JWT_SECRET", "supersecret32characterlongproductionjwtsigningsecret!")
SESSION_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days

# In-memory login attempt rate limiter & lockout store
_login_attempts: Dict[str, list] = defaultdict(list)
_locked_accounts: Dict[str, float] = {}

def check_login_rate_limit(email: str, max_attempts: int = 5, window_sec: int = 900) -> Tuple[bool, int]:
    """
    Enforces maximum 5 failed attempts per 15-minute sliding window.
    Returns: (is_allowed, retry_after_seconds)
    """
    clean_email = email.lower().strip()
    now = time.time()

    if clean_email in _locked_accounts:
        lock_expiry = _locked_accounts[clean_email]
        if now < lock_expiry:
            return False, int(lock_expiry - now)
        else:
            del _locked_accounts[clean_email]
            _login_attempts[clean_email] = []

    attempts = [t for t in _login_attempts[clean_email] if now - t < window_sec]
    _login_attempts[clean_email] = attempts

    if len(attempts) >= max_attempts:
        _locked_accounts[clean_email] = now + window_sec
        return False, window_sec

    return True, 0

def record_failed_login(email: str):
    clean_email = email.lower().strip()
    _login_attempts[clean_email].append(time.time())

def reset_login_attempts(email: str):
    clean_email = email.lower().strip()
    _login_attempts.pop(clean_email, None)
    _locked_accounts.pop(clean_email, None)

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False

def create_session_jwt(user_id: str, email: str, workspace_id: str, is_super_admin: bool = False, role: str = "MEMBER") -> str:
    """Signs a secure HS256 session token with standard issuer and audience claims."""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "userId": user_id,
        "email": email,
        "workspaceId": workspace_id,
        "workspace_id": workspace_id,
        "isSuperAdmin": is_super_admin,
        "is_super_admin": is_super_admin,
        "role": role,
        "iss": "aaas-auth",
        "aud": "aaas-app",
        "iat": now,
        "exp": now + SESSION_EXPIRY_SECONDS
    }
    return jwt.encode(payload, SESSION_JWT_SECRET, algorithm="HS256")

def verify_session_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Verifies and decodes a session JWT."""
    try:
        return jwt.decode(token, SESSION_JWT_SECRET, algorithms=["HS256"], audience="aaas-app", issuer="aaas-auth")
    except Exception:
        # Also support decoding with permissive audience for development compatibility
        try:
            return jwt.decode(token, SESSION_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False, "verify_iss": False})
        except Exception:
            return None
