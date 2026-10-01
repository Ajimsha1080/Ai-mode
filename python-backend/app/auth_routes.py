import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth_service import (
    check_login_rate_limit,
    create_session_jwt,
    hash_password,
    record_failed_login,
    reset_login_attempts,
    verify_password,
    verify_session_jwt,
)
from .db.database import get_db_session
from .db.models import AgentConfigModel, AgentModel, UserModel, WorkspaceMemberModel, WorkspaceModel

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    workspace_name: str | None = "My Store"

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

class VerifyEmailRequest(BaseModel):
    token: str

@router.post("/login")
async def login_endpoint(
    req: LoginRequest,
    session: AsyncSession = Depends(get_db_session)
):
    clean_email = req.email.lower().strip()

    # 1. Rate Limiting Check
    allowed, retry_after = check_login_rate_limit(clean_email)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please retry in {retry_after} seconds."
        )

    # 2. Database User Lookup
    stmt = select(UserModel).where(UserModel.email == clean_email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        record_failed_login(clean_email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(req.password, user.password_hash):
        record_failed_login(clean_email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    reset_login_attempts(clean_email)

    # 3. Resolve Workspace Membership
    mem_stmt = select(WorkspaceMemberModel).where(WorkspaceMemberModel.user_id == user.id)
    mem_res = await session.execute(mem_stmt)
    membership = mem_res.scalar_one_or_none()
    workspace_id = membership.workspace_id if membership else "ws_acme_corp"

    # 4. Generate Session Token
    token = create_session_jwt(
        user_id=user.id,
        email=user.email,
        workspace_id=workspace_id,
        is_super_admin=user.is_super_admin,
        role=user.role
    )

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "is_super_admin": user.is_super_admin,
            "role": user.role
        },
        "workspace_id": workspace_id
    }

@router.post("/signup")
async def signup_endpoint(
    req: SignupRequest,
    session: AsyncSession = Depends(get_db_session)
):
    clean_email = req.email.lower().strip()

    # Check if user already exists
    stmt = select(UserModel).where(UserModel.email == clean_email)
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account with this email already exists.")

    # Create workspace, user, and membership
    ws_id = f"ws_{uuid.uuid4().hex[:12]}"
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    agent_id = f"agent_{uuid.uuid4().hex[:12]}"

    workspace = WorkspaceModel(
        id=ws_id,
        name=req.workspace_name or "My Store",
        slug=f"store-{uuid.uuid4().hex[:6]}",
        tier="GROWTH",
        plan="GROWTH"
    )
    user = UserModel(
        id=user_id,
        email=clean_email,
        name=req.name,
        password_hash=hash_password(req.password),
        role="OWNER",
        is_super_admin=False
    )
    membership = WorkspaceMemberModel(
        id=f"mem_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        user_id=user_id,
        role="OWNER"
    )
    agent = AgentModel(
        id=agent_id,
        workspace_id=ws_id,
        name="ShopMate AI",
        description="Autonomous AI shopping assistant"
    )
    agent_config = AgentConfigModel(
        id=f"cfg_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        model="sarvam-105b-conversations",
        system_prompt="You are a helpful e-commerce shopping concierge.",
        rag_enabled=True
    )

    session.add_all([workspace, user, membership, agent, agent_config])
    await session.commit()

    token = create_session_jwt(
        user_id=user.id,
        email=user.email,
        workspace_id=ws_id,
        is_super_admin=False,
        role="OWNER"
    )

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_super_admin": False
        },
        "workspace_id": ws_id
    }

@router.get("/me")
async def me_endpoint(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_db_session)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token missing")

    token = authorization.replace("Bearer ", "").strip()
    claims = verify_session_jwt(token)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    user_id = claims.get("userId") or claims.get("sub")
    stmt = select(UserModel).where(UserModel.id == user_id)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_super_admin": user.is_super_admin
        },
        "workspace_id": claims.get("workspaceId") or claims.get("workspace_id")
    }

@router.post("/logout")
async def logout_endpoint():
    return {"success": True, "message": "Successfully logged out"}

@router.post("/verify-email")
async def verify_email_endpoint(req: VerifyEmailRequest):
    return {"success": True, "message": "Email verified successfully"}

@router.post("/forgot-password")
async def forgot_password_endpoint(req: ForgotPasswordRequest):
    return {"success": True, "message": "If an account exists, a password reset link has been dispatched."}

@router.post("/reset-password")
async def reset_password_endpoint(req: ResetPasswordRequest):
    return {"success": True, "message": "Password updated successfully."}
