import asyncio
import json
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .agent_runtime import run_agent_cycle
from .ai_mode.routes import router as ai_mode_router
from .audit import get_tenant_audit_logs, record_audit_log
from .auth import require_admin_auth, resolve_agent_chat_auth, verify_service_jwt
from .auth_routes import router as auth_router
from .connectors import router as connectors_router
from .db.database import get_db_session, init_db
from .db.repository import DatabaseRepository
from .llm import LLMClient
from .models import ChatRequest, ChatResponse, KnowledgeIngestRequest, RAGQueryRequest
from .observability import ObservabilityMiddleware
from .rag import execute_rag_pipeline, fetch_tenant_chunks_from_db
from .rate_limiter import rate_limiter
from .tools import _fetch_order_db

_order_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def check_order_rate_limit(client_ip: str, workspace_id: str, limit: int = 10, window_sec: int = 60):
    key = f"{client_ip}:{workspace_id}"
    now = time.time()
    timestamps = [ts for ts in _order_rate_limit_store[key] if now - ts < window_sec]
    if len(timestamps) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Too many order lookup attempts. Please wait before retrying."
        )
    timestamps.append(now)
    _order_rate_limit_store[key] = timestamps


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Enterprise Database Schema & Seeding
    await init_db()
    yield

app = FastAPI(
    title="ShopMate AaaS Enterprise Python AI Engine",
    version="2.0.0",
    description="Enterprise Python FastAPI backend powering Database-backed 12-stage RAG, Multi-step Agent Runtime, and E-commerce Tools.",
    lifespan=lifespan
)

app.add_middleware(ObservabilityMiddleware)
app.include_router(auth_router)
app.include_router(connectors_router)
app.include_router(ai_mode_router)

# Restrict CORS to explicit allowed origins list (Never wildcard with credentials)
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://frontend:3000")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip() and o.strip() != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Workspace-Id", "X-Request-Id"],
)

@app.get("/health")
@app.get("/healthz")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "python-backend",
        "uptime": "OK"
    }

@app.get("/ready")
@app.get("/readyz")
async def readiness_check(session: AsyncSession = Depends(get_db_session)):
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database not ready: {str(e)}") from e

    client = LLMClient()
    app_env = os.getenv("APP_ENV", "development").lower()
    if app_env != "development" and not client.is_configured():
        raise HTTPException(
            status_code=503,
            detail="LLM runtime is not configured for production environment."
        )

    return {
        "status": "READY",
        "database": "CONNECTED",
        "vector_engine": "ACTIVE",
        "llm_runtime": "INITIALIZED" if client.is_configured() else "DEV_FALLBACK"
    }

@app.get("/api/v1/db/status")
async def get_db_status(
    admin_claims: dict[str, Any] = Depends(require_admin_auth),
    session: AsyncSession = Depends(get_db_session)
):
    """Returns the live status of the Enterprise Database (Protected: Admin/Service Token Required)."""
    repo = DatabaseRepository(session)
    products = await repo.get_all_products(workspace_id=admin_claims["workspace_id"])
    chunks = await repo.get_tenant_chunks(workspace_id=admin_claims["workspace_id"])
    return {
        "status": "CONNECTED",
        "workspace_id": admin_claims["workspace_id"],
        "tenant_products": len(products),
        "tenant_knowledge_chunks": len(chunks),
        "persistence": "Enterprise Relational & Vector Storage Active"
    }

@app.get("/api/v1/audit/logs")
async def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin_claims: dict[str, Any] = Depends(require_admin_auth)
):
    """Retrieve audit logs for admin actions scoped strictly to the authenticated workspace."""
    workspace_id = admin_claims["workspace_id"]
    return get_tenant_audit_logs(workspace_id, limit=limit, offset=offset)

@app.post("/api/v1/audit/logs")
async def create_audit_log_entry(
    payload: dict[str, Any],
    admin_claims: dict[str, Any] = Depends(require_admin_auth)
):
    """Record an administrative audit log entry with PII redaction."""
    workspace_id = admin_claims["workspace_id"]
    actor_id = admin_claims.get("sub", "admin_user")
    entry = record_audit_log(
        workspace_id=workspace_id,
        actor_id=actor_id,
        action=payload.get("action", "ADMIN_ACTION"),
        resource_type=payload.get("resource_type", "SYSTEM"),
        resource_id=payload.get("resource_id", "res_default"),
        metadata=payload.get("metadata", {})
    )
    return entry


@app.post("/api/v1/agents/{agent_id}/chat", response_model=ChatResponse)
async def chat_agent(
    agent_id: str,
    req: ChatRequest,
    claims: dict[str, Any] = Depends(resolve_agent_chat_auth)
):
    """
    Executes a full multi-step agent reasoning cycle with 12-stage RAG and tools.
    Workspace ID is strictly derived from verified auth (Service JWT or Public Deployment Key).
    CPU-heavy work is offloaded to a worker thread outside the async event loop.
    """
    token_workspace_id = claims["workspace_id"]
    if req.workspace_id and req.workspace_id != token_workspace_id and claims.get("role") != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Token workspace ({token_workspace_id}) does not match requested workspace ({req.workspace_id})"
        )

    # Enforce Redis-backed per-tenant rate limits and monthly quotas
    await rate_limiter.check_rate_limit(token_workspace_id)

    target_ws = req.workspace_id or token_workspace_id

    try:
        # Offload synchronous/CPU-heavy agent execution to thread pool
        result = await asyncio.to_thread(
            run_agent_cycle,
            agent_id=agent_id,
            message=req.message,
            workspace_id=target_ws,
            conversation_id=req.conversation_id,
            session_id=req.session_id,
            customer_email=req.customer_email,
            context=req.context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/api/v1/agents/{agent_id}/chat/stream")
async def stream_chat_agent(
    agent_id: str,
    req: ChatRequest,
    claims: dict[str, Any] = Depends(resolve_agent_chat_auth)
):
    """
    Streams the agent reasoning cycle token-by-token using Server-Sent Events (SSE).
    """
    token_workspace_id = claims["workspace_id"]
    if req.workspace_id and req.workspace_id != token_workspace_id and claims.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: Cross-tenant workspace mismatch")

    # Enforce Redis-backed per-tenant rate limits and monthly quotas
    await rate_limiter.check_rate_limit(token_workspace_id)

    target_ws = req.workspace_id or token_workspace_id

    async def event_generator():
        # Yield initial connected event
        yield f"event: connect\ndata: {json.dumps({'status': 'CONNECTED', 'workspace_id': target_ws})}\n\n"

        # Execute cycle in threadpool to prevent event loop blocking
        result = await asyncio.to_thread(
            run_agent_cycle,
            agent_id=agent_id,
            message=req.message,
            workspace_id=target_ws,
            conversation_id=req.conversation_id,
            session_id=req.session_id,
            customer_email=req.customer_email,
            context=req.context
        )

        # Stream the full tokens
        response_text = result.get("response", "")
        # Stream in simulated natural chunks
        words = response_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
            await asyncio.sleep(0.01)

        # Final structured payload event
        yield f"event: done\ndata: {json.dumps(result)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/v1/rag/query")
async def query_rag_pipeline(
    req: RAGQueryRequest,
    claims: dict[str, Any] = Depends(verify_service_jwt)
):
    token_workspace_id = claims["workspace_id"]
    if req.workspace_id and req.workspace_id != token_workspace_id and claims.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: Cross-tenant workspace mismatch")

    try:
        chunks = await fetch_tenant_chunks_from_db(token_workspace_id)
        return execute_rag_pipeline(req.question, workspace_id=token_workspace_id, tenant_chunks=chunks, top_k=req.top_k or 3)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/api/v1/knowledge/ingest")
async def ingest_knowledge_endpoint(
    req: KnowledgeIngestRequest,
    claims: dict[str, Any] = Depends(verify_service_jwt),
    session: AsyncSession = Depends(get_db_session)
):
    token_workspace_id = claims["workspace_id"]
    if req.workspace_id and req.workspace_id != token_workspace_id and claims.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: Cross-tenant workspace mismatch")

    target_ws = req.workspace_id or token_workspace_id

    # Split content into distinct paragraphs/chunks
    raw_chunks = [c.strip() for c in req.content.split("\n\n") if c.strip()]
    if not raw_chunks:
        raw_chunks = [req.content]

    chunks_data = []
    for rc in raw_chunks:
        chunks_data.append({
            "text": rc,
            "embedding": [0.0] * 128,
            "metadata": req.metadata or {}
        })

    repo = DatabaseRepository(session)
    doc = await repo.add_knowledge_doc_with_chunks(
        workspace_id=target_ws,
        title=req.title,
        content=req.content,
        chunks=chunks_data
    )
    return {
        "success": True,
        "document_id": doc.id,
        "title": doc.title,
        "chunks_created": len(chunks_data),
        "workspace_id": target_ws
    }

@app.get("/api/v1/orders/{order_number}")
async def get_order_endpoint(
    order_number: str,
    request: Request,
    customer_email: str = Query(..., description="Customer email for verification"),
    claims: dict[str, Any] = Depends(verify_service_jwt)
):
    workspace_id = claims["workspace_id"]
    client_ip = request.client.host if request.client else "unknown_ip"
    check_order_rate_limit(client_ip, workspace_id)

    order = await _fetch_order_db(workspace_id, order_number, customer_email)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order '{order_number}' not found with the provided email address.")
    return order

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
