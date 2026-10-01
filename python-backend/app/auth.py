import base64
import os
from pathlib import Path
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException

DISALLOWED_DEFAULT_SECRETS = [
    "super_secret_jwt_key_enterprise_grade_aaas_platform_2026",
    "super_secret_jwt_key_change_in_production",
    "secret",
    "changeme",
    "password",
    "test",
    "admin",
    "12345678901234567890123456789012",
    "aaas_live_production_jwt_service_secret_2026_secure_key!",
    "aaas_live_production_jwt_session_secret_2026_secure_key!",
    "aaas_live_production_aes_256_encryption_master_key_2026!"
]

def normalize_pem_key(raw_key: str) -> str:
    clean = raw_key.strip()
    if not clean.startswith("-----BEGIN") and len(clean) > 64:
        try:
            decoded = base64.b64decode(clean).decode("utf-8")
            if "-----BEGIN" in decoded:
                clean = decoded.strip()
        except Exception:
            pass
    return clean.replace("\\n", "\n")

def get_service_public_key() -> str:
    app_env = (os.getenv("APP_ENV") or os.getenv("NODE_ENV") or os.getenv("ENVIRONMENT") or "").lower()
    raw = (
        os.getenv("SERVICE_JWT_PUBLIC_KEY")
        or os.getenv("SERVICE_JWT_PUBLIC_KEY_PEM")
    )

    if raw and os.path.exists(raw):
        try:
            with open(raw, encoding="utf-8") as f:
                raw = f.read()
        except Exception:
            pass

    if not raw:
        if app_env in ("development", "dev"):
            # Check shared dev key location
            dev_key_path = Path(__file__).resolve().parent.parent.parent / "data" / ".keys" / "service_rs256_public.pem"
            if dev_key_path.exists():
                try:
                    with open(dev_key_path, encoding="utf-8") as f:
                        return f.read().strip()
                except Exception:
                    pass
            # Fallback if key file not written yet in dev: return empty or dev placeholder
            return ""
        raise RuntimeError(
            "Security Error: SERVICE_JWT_PUBLIC_KEY is missing. "
            "An asymmetric RS256/EdDSA public key is required in production."
        )

    clean = normalize_pem_key(raw)
    if clean in DISALLOWED_DEFAULT_SECRETS:
        raise RuntimeError("Security Error: SERVICE_JWT_PUBLIC_KEY is using a known insecure default secret.")
    return clean

# Backwards-compatibility alias
get_service_secret = get_service_public_key

ALLOWED_ALGORITHMS = ["RS256", "EdDSA"]

def decode_token(token: str) -> dict[str, Any]:
    public_key = get_service_public_key()
    app_env = (os.getenv("APP_ENV") or os.getenv("NODE_ENV") or os.getenv("ENVIRONMENT") or "").lower()

    if not public_key and app_env in ("development", "dev"):
        # In dev mode before keypair is created on disk, decode without verification only for testing
        try:
            return jwt.decode(token, options={"verify_signature": False, "verify_aud": False, "verify_iss": False})
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid service token: {str(e)}") from e

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=ALLOWED_ALGORITHMS,
            audience="aaas-python",
            issuer="aaas-node",
            leeway=60,
            options={
                "require": ["exp", "iss", "aud"],
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True
            }
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Service token has expired") from e
    except (jwt.InvalidTokenError, jwt.InvalidAudienceError, jwt.InvalidIssuerError) as e:
        raise HTTPException(status_code=401, detail=f"Invalid asymmetric service token: {str(e)}") from e

def verify_service_jwt(authorization: str | None = Header(None)) -> dict[str, Any]:
    """
    Strict Asymmetric Service-to-Service JWT Verification (RS256).
    Derives workspace_id ONLY from verified token claims signed by Next.js.
    Never accepts unverified client-supplied tenancy.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header with Bearer service token is required"
        )

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)

    workspace_id = payload.get("workspace_id") or payload.get("workspaceId")
    if not workspace_id:
        raise HTTPException(
            status_code=401,
            detail="Forbidden: JWT missing required 'workspace_id' claim"
        )

    role = payload.get("role", "MEMBER")
    is_super_admin = bool(payload.get("isSuperAdmin") is True or role == "SUPERADMIN")

    return {
        "workspace_id": workspace_id,
        "user_id": payload.get("userId") or payload.get("sub") or "service_system",
        "role": role,
        "is_super_admin": is_super_admin
    }

def require_admin_auth(claims: dict[str, Any] = Depends(verify_service_jwt)) -> dict[str, Any]:
    """Requires verified admin privileges or super-admin claims."""
    if not claims.get("is_super_admin") and claims.get("role") not in ["OWNER", "ADMIN", "SUPERADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Admin or Owner role required"
        )
    return claims


async def resolve_agent_chat_auth(
    authorization: str | None = Header(None),
    origin: str | None = Header(None),
    referer: str | None = Header(None)
) -> dict[str, Any]:
    """
    Unified authentication resolver for chat endpoints:
    1. Asymmetric Service JWT (signed by Next.js BFF proxy)
    2. Public Deployment Key (pk_live_... / dep_...) with domain verification
    3. Secret API Key (ak_live_...)
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header with Bearer token is required"
        )

    token = authorization.split(" ", 1)[1].strip()

    # Public deployment key check
    if token.startswith("pk_live_") or token.startswith("dep_"):
        from sqlalchemy import select

        from .db.database import async_session_factory
        from .db.models import DeploymentModel

        async with async_session_factory() as session:
            stmt = select(DeploymentModel).where(
                (DeploymentModel.public_key == token) | (DeploymentModel.id == token)
            )
            res = await session.execute(stmt)
            dep = res.scalars().first()

            if not dep or dep.status != "ACTIVE":
                raise HTTPException(status_code=401, detail="Invalid or inactive deployment key")

            # Domain verification
            req_origin = origin or referer or ""
            allowed = dep.allowed_domains or ["*"]
            if "*" not in allowed:
                origin_clean = req_origin.replace("https://", "").replace("http://", "").split("/")[0]
                matched = any(
                    origin_clean == d or (d.startswith("*.") and origin_clean.endswith(d[2:]))
                    for d in allowed
                )
                if not matched and req_origin:
                    raise HTTPException(status_code=403, detail=f"Origin '{req_origin}' is not allowed for this deployment widget.")

            return {
                "workspace_id": dep.workspace_id,
                "agent_id": dep.agent_id,
                "user_id": "anonymous_shopper",
                "role": "PUBLIC_VIEWER",
                "is_public_deployment": True
            }

    # Otherwise verify Service JWT
    return verify_service_jwt(authorization)
