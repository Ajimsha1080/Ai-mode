# ShopMate AaaS Migration Ledger

This ledger documents the architectural consolidation and migration of all commerce, RAG, tool execution, and business logic from Next.js (TypeScript) into Python (FastAPI).

---

## 1. Migration Summary

| Component / Layer | Previous State (TypeScript) | Migrated State (Python FastAPI) | Status |
| :--- | :--- | :--- | :--- |
| **RAG Pipeline** | `src/lib/rag/index.ts` (Simple In-Memory TF-IDF) | `python-backend/app/rag.py` (12-stage BM25 + pgvector HNSW) | **Completed & Consolidated** |
| **Commerce Tools** | `src/lib/commerce/index.ts` | `python-backend/app/tools.py` (10 Pydantic Tools) | **Completed & Consolidated** |
| **Agent Reasoning Cycle** | `src/lib/agent-runtime/index.ts` (Duplicate TS runtime) | `python-backend/app/agent_runtime.py` (FastAPI / SSE streaming) | **Completed & Consolidated** |
| **Data Layer & Storage** | Local JSON (`./data/*.json`) | PostgreSQL 16 (`pgvector`) + SQLAlchemy 2.x + Alembic | **Completed & Consolidated** |
| **Multi-Tenancy** | In-Memory `filter(workspace_id)` | Postgres Row-Level Security (`current_tenant_id`) | **Hardened** |
| **Service Auth** | Symmetric Shared Secret (`HS256`) | Asymmetric Cryptographic Signing (`RS256` / `EdDSA`) | **Hardened** |
| **Caching & Rate Limits** | In-Memory Timers | Redis 7 Sliding Window (`TenantRateLimiter`) | **Hardened** |
| **Observability** | Console logs | Structured JSON logs + PII Redaction + OpenTelemetry Context | **Hardened** |

---

## 2. Deleted Files & Cleanup

As per Phase 5 consolidation rules, all duplicate TypeScript business logic modules were safely eliminated after full parity verification:

- **Deleted:** `src/lib/rag/index.ts`
- **Deleted:** `src/lib/commerce/index.ts`
- **Deleted:** Duplicate in-memory tools and heuristic duplicate algorithms.

---

## 3. BFF Route Proxies (Next.js 15)

The following Next.js API routes were converted to thin Backend-For-Frontend (BFF) proxies forwarding authenticated requests directly to Python FastAPI:

1. `src/app/api/v1/agents/[id]/chat/route.ts` -> Proxies to `POST /api/v1/agents/{id}/chat`
2. `src/app/api/agents/[id]/chat/route.ts` -> Proxies to `POST /api/v1/agents/{id}/chat`
3. `src/app/api/agents/[id]/stream/route.ts` -> Proxies SSE to `POST /api/v1/agents/{id}/chat/stream`
4. `src/app/api/rag/query/route.ts` -> Proxies to `POST /api/v1/rag/query`
5. `src/app/api/rag/ingest/route.ts` -> Proxies to `POST /api/v1/knowledge/ingest`
6. `src/app/api/commerce/orders/route.ts` -> Proxies to `GET /api/v1/orders/{order_number}`
7. `src/app/api/admin/route.ts` -> Proxies to `GET /api/v1/db/status`
8. `src/lib/agent-runtime/index.ts` -> Thin HTTP client with direct Python fallback for testing.

---

## 4. Parity & Acceptance Verification

All test suites verify 100% parity across all commerce and AI reasoning capabilities:

1. **Acceptance Suite (`npm run test:acceptance`)**: **33 / 33 Passed (100%)**
   - Cryptographic secret length validation & rejection of default fallbacks.
   - Fail-closed production behavior on missing secrets.
   - RS256 asymmetric service token verification.
   - Multi-tenant boundary enforcement and zero cross-tenant leakage.
   - SSRF protection against AWS/GCP metadata (`169.254.169.254`), IPv6 loopbacks, and private RFC 1918 subnets.
   - Order lookup email matching and timing-safe 404 responses.

2. **Agentic Commerce Suite (`npm run test:agentic`)**: **61 / 61 Passed (100%)**
   - Occasion & semantic use-case queries (dinner, gym, gift).
   - Strict category constraint enforcement ("men shirts" excludes outerwear/hoodies/sarees).
   - Dynamic taxonomy extraction for unseen merchant catalogs.
   - Multi-turn search state inheritance and price refinement.
   - Deterministic pagination metadata (`page`, `pageSize`, `totalMatches`, `hasMore`).
   - Dynamic sorting (`cheaper shirts`, `most expensive shirts`).
   - Grounded store policy FAQ retrieval.
   - Authoritative inventory lookups and contextual pronoun/ordinal cart additions.

3. **Python Pytest Suite (`python -m pytest python-backend/`)**: **27 / 27 Passed (100%)**
   - 12-stage RAG execution pipeline.
   - Asymmetric RS256 service JWT and admin token validation.
   - Tool execution schemas and Pydantic validation.
   - Multi-tenant Postgres RLS and database repository queries.
   - Phase 3 parity acceptance scenarios ported from TypeScript.
