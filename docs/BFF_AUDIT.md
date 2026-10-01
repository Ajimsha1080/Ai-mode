# Backend for Frontend (BFF) Architecture & API Route Audit

## 1. Executive Summary

This audit verifies the transition of the ShopMate (AI-Native-Ecommerce / Ai-mode) Next.js codebase to a thin BFF (Backend for Frontend) proxy. All AI orchestration (RAG retrieval, BM25, vector search, multi-turn state, LLM generation), commerce database transactions, and connector operations have been consolidated into the Python FastAPI backend of record (`python-backend/`).

---

## 2. Codebase Audit for Database, Secrets, & LLM Dependencies (`src/`)

| Checked Pattern / Dependency | Locations Found | Role & Architecture Status |
| :--- | :--- | :--- |
| **`DATABASE_URL` / Postgres / ORM** | None in `src/` runtime paths | Next.js does not connect to Postgres. All DB transactions (SQLAlchemy 2.x + Alembic) are isolated within `python-backend/app/db/`. |
| **`prisma` / `drizzle` / `pg`** | None in `src/` | No direct Node.js DB drivers are utilized. |
| **Direct LLM Calls (`openai`, `anthropic`, `sarvam`)** | UI dropdowns and test mocks only | All LLM invocation and streaming occurs in `python-backend/app/agent_loop.py` & `rag.py`. Node forwards SSE streams directly. |
| **`ENCRYPTION_KEY`** | `src/lib/crypto/encryption.ts` (Dev test helper only) | Removed from `frontend` container in `docker-compose.yml`. Secrets encryption occurs within `python-backend/app/crypto/`. |
| **`REDIS_URL`** | Removed from frontend container | Rate limiting, quota tracking, and session caching are managed centrally by `python-backend/app/redis_client.py`. |
| **Asymmetric Service Auth** | `src/lib/auth/index.ts` (`createServiceJwt`) | Next.js signs asymmetric RS256 service tokens using `SERVICE_JWT_PRIVATE_KEY`; FastAPI verifies using `SERVICE_JWT_PUBLIC_KEY`. |

---

## 3. Comprehensive `src/app/api/` Route Matrix

| Next.js API Route | HTTP Methods | Proxied to FastAPI? | Target FastAPI Endpoint | Auth / Context Mode |
| :--- | :--- | :--- | :--- | :--- |
| `/api/actions/permissions` | `GET`, `POST` | Yes | `/api/v1/permissions` | Service JWT (RS256) |
| `/api/admin` | `GET`, `POST` | Yes | `/api/v1/admin` | SuperAdmin Service JWT |
| `/api/agents` | `GET`, `POST` | Yes | `/api/v1/agents/` | Service JWT (RS256) |
| `/api/agents/[id]` | `GET`, `PUT`, `DELETE` | Yes | `/api/v1/agents/{id}` | Service JWT (RS256) |
| `/api/agents/[id]/chat` | `POST` | Yes | `/api/v1/agents/{id}/chat` | Service JWT (RS256) |
| `/api/agents/[id]/stream` | `POST` | Yes (SSE Stream) | `/api/v1/agents/{id}/stream` | Service JWT + Direct SSE Pipe |
| `/api/agents/[id]/versions` | `GET`, `POST` | Yes | `/api/v1/agents/{id}/versions` | Service JWT (RS256) |
| `/api/analytics` | `GET` | Yes | `/api/v1/analytics` | Service JWT (RS256) |
| `/api/api-keys` | `GET`, `POST`, `DELETE` | Yes | `/api/v1/api-keys` | Service JWT (RS256) |
| `/api/audit-logs` | `GET` | Yes | `/api/v1/audit-logs` | Service JWT (RS256) |
| `/api/auth/login` | `POST` | Yes | `/api/v1/auth/login` | Public -> Issues HTTP-only Cookie |
| `/api/auth/signup` | `POST` | Yes | `/api/v1/auth/signup` | Public -> Auto-creates Workspace & Owner |
| `/api/auth/me` | `GET` | Yes | `/api/v1/auth/me` | Session Cookie (`aaas_session_token`) |
| `/api/auth/logout` | `POST` | Yes | `/api/v1/auth/logout` | Clears Session Cookie |
| `/api/auth/forgot-password` | `POST` | Yes | `/api/v1/auth/forgot-password` | Public Rate-Limited |
| `/api/auth/reset-password` | `POST` | Yes | `/api/v1/auth/reset-password` | Public Token Auth |
| `/api/auth/verify-email` | `GET`, `POST` | Yes | `/api/v1/auth/verify-email` | Public Token Auth |
| `/api/billing` | `GET`, `POST` | Yes | `/api/v1/billing` | Service JWT (RS256) |
| `/api/billing/checkout` | `POST` | Yes | `/api/v1/billing/checkout` | Service JWT (RS256) |
| `/api/billing/portal` | `POST` | Yes | `/api/v1/billing/portal` | Service JWT (RS256) |
| `/api/commerce/products` | `GET`, `POST` | Yes | `/api/v1/products/` | Service JWT (RS256) |
| `/api/commerce/orders` | `GET`, `POST` | Yes | `/api/v1/orders/` | Service JWT (RS256) |
| `/api/commerce/sync` | `POST` | Yes | `/api/v1/connectors/sync-all` | Service JWT (RS256) |
| `/api/conversations` | `GET`, `POST` | Yes | `/api/v1/conversations/` | Service JWT (RS256) |
| `/api/conversations/[id]` | `GET`, `DELETE` | Yes | `/api/v1/conversations/{id}` | Service JWT (RS256) |
| `/api/deployments` | `GET`, `POST` | Yes | `/api/v1/deployments` | Service JWT (RS256) |
| `/api/deployments/resolve` | `GET` | Yes | `/api/v1/deployments/resolve` | Public Token Resolution |
| `/api/evaluations` | `GET`, `POST` | Yes | `/api/v1/evaluations` | Service JWT (RS256) |
| `/api/health` | `GET` | Node Healthcheck | N/A | Local Process Health |
| `/api/ready` | `GET` | Upstream Health | `/healthz` | Checks FastAPI Upstream |
| `/api/integrations` | `GET` | Yes | `/api/v1/connectors/` | Service JWT (RS256) |
| `/api/integrations/sync-all` | `POST` | Yes | `/api/v1/connectors/sync-all` | Service JWT (RS256) |
| `/api/integrations/[id]/connect` | `POST` | Yes | `/api/v1/connectors/{id}/connect` | Service JWT (RS256) |
| `/api/integrations/[id]/disconnect` | `POST` | Yes | `/api/v1/connectors/{id}/disconnect` | Service JWT (RS256) |
| `/api/integrations/[id]/logs` | `GET` | Yes | `/api/v1/connectors/{id}/logs` | Service JWT (RS256) |
| `/api/integrations/[id]/logs/replay` | `POST` | Yes | `/api/v1/connectors/{id}/logs/replay` | Service JWT (RS256) |
| `/api/integrations/[id]/sync` | `POST` | Yes | `/api/v1/connectors/{id}/sync` | Service JWT (RS256) |
| `/api/knowledge` | `GET`, `POST` | Yes | `/api/v1/knowledge` | Service JWT (RS256) |
| `/api/knowledge/sync` | `POST` | Yes | `/api/v1/knowledge/sync` | Service JWT (RS256) |
| `/api/rag/ingest` | `POST` | Yes | `/api/v1/rag/ingest` | Service JWT (RS256) |
| `/api/rag/query` | `POST` | Yes | `/api/v1/rag/query` | Service JWT (RS256) |
| `/api/settings` | `GET`, `PUT` | Yes | `/api/v1/settings` | Service JWT (RS256) |
| `/api/settings/members` | `GET`, `POST`, `DELETE` | Yes | `/api/v1/settings/members` | Service JWT (RS256) |
| `/api/tenant/delete` | `POST` | Yes | `/api/v1/tenant/delete` | Service JWT (RS256) |
| `/api/tenant/export` | `GET` | Yes | `/api/v1/tenant/export` | Service JWT (RS256) |
| `/api/v1/agents/[id]/chat` | `POST` | Yes | `/api/v1/agents/{id}/chat` | Service JWT (RS256) |
| `/api/webhooks` | `POST` | Yes | `/api/v1/webhooks/incoming` | HMAC Signature Verification |
| `/api/webhooks/razorpay` | `POST` | Yes | `/api/v1/webhooks/razorpay` | Razorpay HMAC Verification |
| `/api/webhooks/stripe` | `POST` | Yes | `/api/v1/webhooks/stripe` | Stripe Signature Verification |

---

## 4. Verification & Testing

All unit tests and end-to-end integration suites confirm that Next.js acts as a decoupled BFF layer without leaking credentials or database connection pools.
