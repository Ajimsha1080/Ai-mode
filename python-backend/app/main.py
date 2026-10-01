import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ChatRequest, ChatResponse, RAGQueryRequest, KnowledgeIngestRequest
from .agent_runtime import run_agent_cycle
from .rag import execute_rag_pipeline
from .tools import lookup_order
from .db.database import init_db, get_db_session
from .db.repository import DatabaseRepository
from .auth import verify_service_jwt, require_admin_auth
from .llm import LLMClient

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
def health_check():
    return {
        "status": "HEALTHY",
        "service": "python-backend",
        "uptime": "OK"
    }

@app.get("/ready")
async def readiness_check(session: AsyncSession = Depends(get_db_session)):
    try:
        from sqlalchemy import text
        await session.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database not ready: {str(e)}")

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
    admin_claims: Dict[str, Any] = Depends(require_admin_auth),
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

from .rate_limiter import rate_limiter
from .auth import verify_service_jwt, require_admin_auth, resolve_agent_chat_auth


@app.post("/api/v1/agents/{agent_id}/chat", response_model=ChatResponse)
async def chat_agent(
    agent_id: str,
    req: ChatRequest,
    claims: Dict[str, Any] = Depends(resolve_agent_chat_auth)
):
    """
    Executes a full multi-step agent reasoning cycle with 12-stage RAG and tools.
    Workspace ID is strictly derived from verified auth (Service JWT or Public Deployment Key).
    CPU-heavy work is offloaded to a worker thread outside the async event loop.
    """
    token_workspace_id = claims["workspace_id"]
    if req.workspace_id and req.workspace_id != token_workspace_id and claims.get("role") != "SUPERADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: Cross-tenant workspace mismatch")

    # Rate limit check per tenant
    allowed, remaining, retry_after = rate_limiter.check_rate_limit(token_workspace_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for workspace. Please retry in {retry_after} seconds."
        )

    try:
        # Offload CPU work (embedding generation, ranking, tool execution) to thread pool
        result = await asyncio.to_thread(
            run_agent_cycle,
            agent_id=agent_id,
            message=req.message,
            conversation_id=req.conversation_id,
            workspace_id=token_workspace_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/agents/{agent_id}/chat/stream")
async def chat_agent_stream(
    agent_id: str,
    req: ChatRequest,
    claims: Dict[str, Any] = Depends(resolve_agent_chat_auth)
):
    token_workspace_id = claims["workspace_id"]
    if req.workspace_id and req.workspace_id != token_workspace_id and claims.get("role") != "SUPERADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: Cross-tenant workspace mismatch")

    # Rate limit check per tenant
    allowed, remaining, retry_after = rate_limiter.check_rate_limit(token_workspace_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for workspace. Please retry in {retry_after} seconds."
        )

    async def event_generator():
        # Offload CPU work to thread pool
        result = await asyncio.to_thread(
            run_agent_cycle,
            agent_id=agent_id,
            message=req.message,
            conversation_id=req.conversation_id,
            workspace_id=token_workspace_id
        )

        yield f"event: stage\ndata: {json.dumps({'stage': 'INTENT_UNDERSTANDING', 'intent': result.get('intent')})}\n\n"
        await asyncio.sleep(0.01)

        if result.get("trace", {}).get("retrieved_citations"):
            yield f"event: stage\ndata: {json.dumps({'stage': 'RAG_RETRIEVAL', 'citations': len(result['trace']['retrieved_citations'])})}\n\n"
            await asyncio.sleep(0.01)

        full_text = result.get("response", "")
        words = full_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
            await asyncio.sleep(0.01)

        yield f"event: done\ndata: {json.dumps(result)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/v1/rag/query")
async def query_rag_pipeline(
    req: RAGQueryRequest,
    claims: Dict[str, Any] = Depends(verify_service_jwt)
):
    token_workspace_id = claims["workspace_id"]
    if req.workspace_id and req.workspace_id != token_workspace_id and claims.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: Cross-tenant workspace mismatch")

    try:
        from .rag import fetch_tenant_chunks_from_db
        chunks = await fetch_tenant_chunks_from_db(token_workspace_id)
        return execute_rag_pipeline(req.question, workspace_id=token_workspace_id, tenant_chunks=chunks, top_k=req.top_k or 3)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/knowledge/ingest")
async def ingest_knowledge_endpoint(
    req: KnowledgeIngestRequest,
    claims: Dict[str, Any] = Depends(verify_service_jwt),
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

import time
from collections import defaultdict
from fastapi import Request

_order_rate_limit_store = defaultdict(list)

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

@app.get("/api/v1/orders/{order_number}")
async def get_order_endpoint(
    order_number: str,
    request: Request,
    customer_email: str = Query(..., description="Customer email for verification"),
    claims: Dict[str, Any] = Depends(verify_service_jwt)
):
    workspace_id = claims["workspace_id"]
    client_ip = request.client.host if request.client else "unknown_ip"
    check_order_rate_limit(client_ip, workspace_id)

    from .tools import _fetch_order_db
    order = await _fetch_order_db(workspace_id, order_number, customer_email)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order '{order_number}' not found with the provided email address.")
    return order

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
