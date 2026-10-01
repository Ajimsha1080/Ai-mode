import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth_service import create_session_jwt, hash_password
from app.db.database import Base, async_session_factory, engine
from app.db.models import UserModel, WorkspaceMemberModel, WorkspaceModel
from app.main import app


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed test user and workspace with unique email
    u_suffix = uuid.uuid4().hex[:6]
    ws_id = f"ws_auth_{u_suffix}"
    usr_id = f"usr_auth_{u_suffix}"
    email = f"sarah.tester.{u_suffix}@gmail.com"

    async with async_session_factory() as session:
        ws = WorkspaceModel(id=ws_id, name="Auth Store", slug=f"auth-store-{u_suffix}")
        user = UserModel(
            id=usr_id,
            email=email,
            name="Sarah Tester",
            password_hash=hash_password("Password123!"),
            role="OWNER"
        )
        mem = WorkspaceMemberModel(id=f"mem_{u_suffix}", workspace_id=ws_id, user_id=usr_id, role="OWNER")
        session.add_all([ws, user, mem])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.test_email = email
        ac.test_user_id = usr_id
        ac.test_ws_id = ws_id
        yield ac

@pytest.mark.asyncio
async def test_auth_login_success(client: AsyncClient):
    res = await client.post("/api/v1/auth/login", json={
        "email": client.test_email,
        "password": "Password123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["email"] == client.test_email
    assert data["workspace_id"] == client.test_ws_id

@pytest.mark.asyncio
async def test_auth_login_invalid_password(client: AsyncClient):
    res = await client.post("/api/v1/auth/login", json={
        "email": client.test_email,
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert "Invalid" in res.json()["detail"]

@pytest.mark.asyncio
async def test_auth_me_endpoint(client: AsyncClient):
    token = create_session_jwt(client.test_user_id, client.test_email, client.test_ws_id)
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["authenticated"] is True
    assert data["user"]["id"] == client.test_user_id

@pytest.mark.asyncio
async def test_auth_signup_endpoint(client: AsyncClient):
    new_email = f"merchant_{uuid.uuid4().hex[:6]}@example.com"
    res = await client.post("/api/v1/auth/signup", json={
        "email": new_email,
        "password": "SecurePassword123!",
        "name": "New Merchant",
        "workspace_name": "New Shop"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["email"] == new_email
