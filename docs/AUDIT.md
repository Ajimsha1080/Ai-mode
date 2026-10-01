# Comprehensive Technical Audit: TypeScript vs. Python Runtime & Architecture

**Date:** October 2026  
**Repository:** `AI-Native-Ecommerce` (ShopMate AaaS)  
**Target:** Python FastAPI as Single Source of Truth for Business & AI Logic  

---

## 1. Complete API Route Audit (`src/app/api/`)

Below is the exhaustive inventory of all 50 API route handlers in `src/app/api/` and their interaction with `PYTHON_BACKEND_URL`:

| Route Path | Method(s) | Calls `PYTHON_BACKEND_URL`? | Purpose & Runtime Execution |
| :--- | :--- | :--- | :--- |
| `src/app/api/actions/permissions/route.ts` | GET, POST | **NO** | Evaluates action permissions against `db.agent_actions`. Pure TypeScript. |
| `src/app/api/admin/route.ts` | GET | **NO** | Aggregates system metrics, workspace count, and active users from `db`. Pure TypeScript. |
| `src/app/api/agents/route.ts` | GET, POST | **NO** | CRUD for agents in `db.agents`. Pure TypeScript. |
| `src/app/api/agents/[id]/route.ts` | GET, PUT, DELETE | **NO** | Agent detail and configuration management in `db.agents` / `db.agent_configs`. Pure TypeScript. |
| `src/app/api/agents/[id]/chat/route.ts` | POST | **YES** | Studio/Playground chat. Calls `POST ${PYTHON_BACKEND_URL}/api/v1/agents/${id}/chat` (6s timeout); falls back to TS `runAgentCycle`. |
| `src/app/api/agents/[id]/stream/route.ts` | POST | **YES** | Real-time SSE chat. Calls `POST ${PYTHON_BACKEND_URL}/api/v1/agents/${id}/chat/stream`; falls back to TS `ReadableStream`. |
| `src/app/api/agents/[id]/versions/route.ts` | GET, POST | **NO** | Agent version rollback and history in `db.agent_versions`. Pure TypeScript. |
| `src/app/api/analytics/route.ts` | GET | **NO** | Computes token usage, latency percentiles, and intent counts from `db.traces`. Pure TypeScript. |
| `src/app/api/api-keys/route.ts` | GET, POST, DELETE | **NO** | Generates SHA-256 hashed merchant API keys in `db.api_keys`. Pure TypeScript. |
| `src/app/api/audit-logs/route.ts` | GET | **NO** | Queries administrative and mutation logs from `db.audit_logs`. Pure TypeScript. |
| `src/app/api/auth/forgot-password/route.ts` | POST | **NO** | Creates password reset tokens in `db.password_resets`. Pure TypeScript. |
| `src/app/api/auth/login/route.ts` | POST | **NO** | Verifies password with `bcryptjs` and signs jose session JWT in `aaas_session_token`. Pure TypeScript. |
| `src/app/api/auth/logout/route.ts` | POST | **NO** | Clears session cookie. Pure TypeScript. |
| `src/app/api/auth/me/route.ts` | GET | **NO** | Decodes session cookie and returns authenticated user and workspace profile. Pure TypeScript. |
| `src/app/api/auth/reset-password/route.ts` | POST | **NO** | Verifies reset token and updates password hash in `db.users`. Pure TypeScript. |
| `src/app/api/auth/signup/route.ts` | POST | **NO** | Creates workspace, owner user, initial agent, and seed data in `db`. Pure TypeScript. |
| `src/app/api/auth/verify-email/route.ts` | POST | **NO** | Validates email verification token in `db.users`. Pure TypeScript. |
| `src/app/api/billing/route.ts` | GET | **NO** | Reads plan tier and quotas from `db.workspaces`. Pure TypeScript. |
| `src/app/api/billing/checkout/route.ts` | POST | **NO** | Generates Stripe/Razorpay payment sessions. Pure TypeScript. |
| `src/app/api/billing/portal/route.ts` | POST | **NO** | Redirects to billing customer portal. Pure TypeScript. |
| `src/app/api/commerce/orders/route.ts` | GET | **NO** | Queries orders via `commerceEngine.getOrder`. Pure TypeScript. |
| `src/app/api/commerce/products/route.ts` | GET, POST | **NO** | Queries product catalog via `commerceEngine.searchProductsDetailed`. Pure TypeScript. |
| `src/app/api/commerce/sync/route.ts` | POST | **NO** | Shopify/WooCommerce catalog synchronization. Pure TypeScript. |
| `src/app/api/conversations/route.ts` | GET, POST | **NO** | Lists/creates customer conversations in `db.conversations`. Pure TypeScript. |
| `src/app/api/conversations/[id]/route.ts` | GET, DELETE | **NO** | Fetches turn messages for conversation in `db.messages`. Pure TypeScript. |
| `src/app/api/deployments/route.ts` | GET, POST, DELETE | **NO** | Manages web widget deployment tokens in `db.deployments`. Pure TypeScript. |
| `src/app/api/deployments/resolve/route.ts` | GET | **NO** | Resolves public widget config by `pk_live_` or `dep_` key. Pure TypeScript. |
| `src/app/api/evaluations/route.ts` | GET, POST | **NO** | Executes golden dataset accuracy evaluations in TS runtime. Pure TypeScript. |
| `src/app/api/health/route.ts` | GET | **NO** | Basic Node.js health probe. Pure TypeScript. |
| `src/app/api/integrations/route.ts` | GET, POST | **NO** | CRUD for third-party platform integrations in `db.integrations`. Pure TypeScript. |
| `src/app/api/integrations/sync-all/route.ts` | POST | **NO** | Batch triggers sync jobs across integrations. Pure TypeScript. |
| `src/app/api/integrations/[id]/connect/route.ts` | POST | **NO** | Connects OAuth / API credentials for integration. Pure TypeScript. |
| `src/app/api/integrations/[id]/disconnect/route.ts` | POST | **NO** | Revokes integration status. Pure TypeScript. |
| `src/app/api/integrations/[id]/logs/route.ts` | GET | **NO** | Queries sync audit events in `db`. Pure TypeScript. |
| `src/app/api/integrations/[id]/logs/replay/route.ts` | POST | **NO** | Re-executes webhook payload. Pure TypeScript. |
| `src/app/api/integrations/[id]/sync/route.ts` | POST | **NO** | Triggers single integration sync. Pure TypeScript. |
| `src/app/api/knowledge/route.ts` | GET, POST, DELETE | **NO** | Ingests text/raw documents into `db.knowledge_chunks`. Pure TypeScript. |
| `src/app/api/knowledge/sync/route.ts` | POST | **NO** | Web crawler that extracts HTML / Schema.org JSON-LD and creates chunks in `db`. Pure TypeScript. |
| `src/app/api/rag/ingest/route.ts` | POST | **NO** | Calls TS `ingestDocument` in `src/lib/rag`. Pure TypeScript. |
| `src/app/api/rag/query/route.ts` | POST | **YES** | Calls `POST ${PYTHON_BACKEND_URL}/api/v1/rag/query` (6s timeout); falls back to TS `executeRAGPipeline`. |
| `src/app/api/ready/route.ts` | GET | **YES** | Readiness probe checking local DB + `GET ${PYTHON_BACKEND_URL}/health`. |
| `src/app/api/settings/route.ts` | GET, PUT | **NO** | Workspace settings and configuration in `db.workspaces`. Pure TypeScript. |
| `src/app/api/settings/members/route.ts` | GET, POST, DELETE | **NO** | Workspace team member management in `db.users`. Pure TypeScript. |
| `src/app/api/tenant/delete/route.ts` | POST | **NO** | Cascades deletion of all tenant data across collections in `db`. Pure TypeScript. |
| `src/app/api/tenant/export/route.ts` | GET | **NO** | Generates GDPR/compliance JSON export of tenant database records. Pure TypeScript. |
| `src/app/api/v1/agents/[id]/chat/route.ts` | POST | **NO** | External API & Web Widget live chat endpoint. Directly executes TS `runAgentCycle`. **Never calls Python backend**. |
| `src/app/api/webhooks/route.ts` | POST | **NO** | Custom generic webhook receiver. Pure TypeScript. |
| `src/app/api/webhooks/razorpay/route.ts` | POST | **NO** | Razorpay HMAC-SHA256 signature verification and order capture in `db`. Pure TypeScript. |
| `src/app/api/webhooks/stripe/route.ts` | POST | **NO** | Stripe webhook signature verification and subscription provisioning. Pure TypeScript. |

---

## 2. Implementation Diff: TypeScript vs. Python

| Subsystem | Exists Only in TypeScript | Exists Only in Python | Exists in Both | Consolidation Priority |
| :--- | :--- | :--- | :--- | :--- |
| **RAG Retrieval** | • Autonomous web crawler with link discovery & Schema.org extractor.<br>• PDF text parsing (`pdf-parse`).<br>• In-memory `db.knowledge_chunks` sync. | • OpenAI `text-embedding-3-small` API integration.<br>• Reciprocal Rank Fusion ($k=60$) rank merging.<br>• `<<<UNTRUSTED_CATALOG_DATA>>>` prompt injection protection.<br>• SQLAlchemy SQL join (`KnowledgeChunkModel` + `KnowledgeDocModel` + `KnowledgeSourceModel`). | • 128-dim polynomial n-gram hashing embedding fallback.<br>• Cosine similarity computation.<br>• Keyword/token overlap scoring.<br>• Zero-knowledge safe fallback responses. | High: Move all ingestion and RAG retrieval exclusively to Python. Replace hashing with real embedding provider. |
| **Product Search & Filtering** | • Runtime schema introspection (`introspectSchema`).<br>• 22+ spelling typo correction dictionary.<br>• English word stemmer (`stemWord`).<br>• Gender resolution (`men`, `women`, `unisex`, `kids`).<br>• Category negation (`"not jackets"`).<br>• Price range constraints (`under`, `between`, currency symbols).<br>• Variant attribute matching (sizes, colors, materials, occasions).<br>• Deterministic sorting (`price_asc`, `price_desc`, `relevance`, `newest`).<br>• Product comparison matrix generator (`compareProducts`). | • Database-backed `ProductModel` SQL queries. | • Basic keyword-to-title matching.<br>• Product detail lookup. | Critical: Port TS schema introspection, typo map, stemmer, constraint parsing, and comparison logic into Python `tools.py`. |
| **Intent Parsing** | • 8 granular intent classes (`PRODUCT_SEARCH`, `PRODUCT_COMPARISON`, `INVENTORY_CHECK`, `CART_ACTION`, `ORDER_TRACKING`, `RETURN_OR_POLICY_INQUIRY`, `HUMAN_HANDOFF`, `GENERAL_CONVERSATION`).<br>• Scope classifier (`recommendations`, `all_matching`, `similar`, `refinement`, `pagination`).<br>• Compound term normalization (`t-shirt`, `tshirt`, `tee`). | • LLM Function Calling tool definitions for Sarvam AI 105B, OpenAI, Anthropic, Ollama.<br>• System prompt injection defense instruction set. | • Return/policy intent regex.<br>• Human operator escalation regex.<br>• Order number regex (`#\d+`). | High: Consolidate intent parsing into Python agent runtime, combining regex pre-filters with LLM tool calling. |
| **Pagination & Multi-Turn State** | • Contextual search state preservation across turns (`last_search_state`).<br>• Ordinal resolution (`"first"`, `"2nd"`, `"third"`, `"last"`).<br>• Contextual pronoun resolution (`"is this in stock?"`).<br>• Color-referenced item resolution (`"the red one"`).<br>• Deterministic pagination metadata (`page`, `pageSize`, `hasMore`, `totalMatches`). | *None* (Python runtime currently executes statelessly per request). | *None* | Critical: Port multi-turn conversation memory, ordinal resolvers, and pagination state into Python runtime. |
| **Order Tracking** | • Dynamic tracking timeline generator (carrier milestones, delivery estimations).<br>• Public status lookup without requiring customer email. | • PII address masking in SQL response.<br>• Mandatory dual-key authentication (`order_number` + `customer_email`). | • Order lookup by `#number` or `ord_` ID.<br>• Carrier detection (`Bluedart`, `Delhivery`). | Medium: Port timeline milestones to Python and standardize PII masking. |
| **Inventory & Variants** | • Multi-variant attribute stock levels (e.g. size `'M'` in color `'Black'`).<br>• SKU-level inventory decrement. | • Product-level stock count on `ProductModel`. | • Product ID lookup and boolean `in_stock` check. | High: Expand Python `ProductModel` and `check_inventory` tool to support variant-level stock attributes. |
| **Authentication & Sessions** | • User login/signup with `bcryptjs` password hashing.<br>• jose session cookie management (`aaas_session_token`).<br>• Merchant API key generation & SHA-256 verification.<br>• Public deployment key verification (`pk_live_`, `dep_`).<br>• Symmetric HS256 service JWT creation (`createServiceJwt`). | • FastAPI dependency `verify_service_jwt` & `require_admin_auth`.<br>• Token claim validation (`workspace_id`, `role`, `user_id`). | • HS256 service JWT validation.<br>• Insecure fallback secret in dev mode (`"development_only_service_secret_32bytes_long!"`). | High: Migrate service JWT from symmetric HS256 to asymmetric (RS256 or EdDSA). Next.js signs with private key; FastAPI verifies with public key. |
| **Tenant Isolation** | • Manual array filtering `db.collection.filter(x => x.workspace_id === workspaceId)`.<br>• Fallback to default tenant `'ws_acme_corp'` if unauthenticated in `/api/agents/[id]/chat`. | • JWT claim verification strictly bound to token `workspace_id`.<br>• 403 Forbidden on cross-tenant mismatch.<br>• SQL queries scoped with `.where(Model.workspace_id == workspace_id)`. | • Scoping data by `workspace_id`. | Critical: Eliminate TS fallback tenant default. Move all DB access to Postgres RLS in Python. |

---

## 3. Verification of "12 Stages" in `python-backend/app/rag.py`

The table below audits every stage in the Python RAG pipeline:

| Stage # | Stage Name | Implementation Status in `rag.py` | Details / Gaps Identified |
| :---: | :--- | :--- | :--- |
| **1** | **Query Understanding & Intent Detection** | **IMPLEMENTED (Heuristic)** | Uses basic regex for `RETURN_OR_POLICY_INQUIRY`, `SHIPPING_LOGISTICS`, `SIZING_FIT`. Hardcodes confidence to `0.95`. Lacks entity extraction for sizes, prices, colors, or gender. |
| **2** | **Query Rewriting & Synonym Expansion** | **IMPLEMENTED (Static)** | Appends hardcoded term arrays (`"store return policy"`, `"warranty terms"`). Lacks dynamic synonym expansion. |
| **3** | **Dense Vector Retrieval** | **IMPLEMENTED (Fallback)** | Uses OpenAI API if key exists; falls back to 128-dim n-gram polynomial hashing with cosine similarity. |
| **4** | **Sparse Token Retrieval** | **STUB / INCOMPLETE** | Naive token substring count in chunk text (`sum(1.0 for t in sparse_tokens if any(t in w ...))`). **Not true BM25** (no IDF weighting, no document length normalization). |
| **5** | **Reciprocal Rank Fusion (RRF)** | **IMPLEMENTED** | Merges dense and sparse ranks correctly using $RRF(d) = \sum \frac{1}{k + r(d)}$ with $k=60$. |
| **6** | **Cross-Encoder Reranking** | **STUB / HEURISTIC** | Linear formula boost (`cand["rrf_score"] * 10.0 + hits...`). **No cross-encoder model is executed**. |
| **7** | **Context Assembly & Boundary Defense** | **IMPLEMENTED** | Formats retrieved chunks inside `<<<UNTRUSTED_CATALOG_DATA>>>` delimiters with source document headers. |
| **8** | **Answer Synthesis** | **STUB / MISSING** | Simply assigns `natural_answer = reranked[0]['chunk_text']` (verbatim first chunk). Does **not** synthesize answers via LLM. |
| **9** | **Grounding & Entailment Verification** | **IMPLEMENTED (Heuristic)** | Calculates token overlap between sentences and context (>20% overlap considered verified). |
| **10** | **Citation Attribution** | **IMPLEMENTED** | Returns list of top $k$ chunks with relevance scores and grounding boolean. |
| **11** | **Safety Guardrail / Policy Compliance** | **PHANTOM / NOT IMPLEMENTED** | Described in documentation, but handled outside `rag.py` via hardcoded strings in `agent_runtime.py`. |
| **12** | **Multi-Tenant Scoping & Cache Invalidation** | **PARTIAL** | Enforces `workspace_id` in SQL queries, but LRU embedding cache is global across tenants without tenant prefixing. |

---

## 4. Tenant Isolation Audit on Live Chat Paths

1. **Internal / Studio Live Chat (`/api/agents/[id]/chat`)**:
   - **Vulnerability**: If `session?.workspaceId` is missing, it falls back to querying `db.agents` or assigns `'ws_acme_corp'` as the default workspace.
   - Signs an HS256 service JWT with the resolved `workspace_id` and calls Python FastAPI.
   - If Python fails, it falls back to TS `runAgentCycle` using in-memory array filtering.

2. **Live Streaming Route (`/api/agents/[id]/stream`)**:
   - Requires valid session (`getAuthSession`), rejects with 401 if missing.
   - Passes token to Python `/api/v1/agents/{id}/chat/stream`.

3. **Public Widget / Customer API (`/api/v1/agents/[id]/chat`)**:
   - Enforces Bearer token verification against `db.deployments` or `db.api_keys`.
   - Resolves `workspace_id` from the deployment record and checks origin domain whitelist.
   - **Critical Architectural Flaw**: Executes TS `runAgentCycle` directly; **never calls Python backend**.

4. **Python FastAPI Backend (`python-backend/app/main.py`)**:
   - Enforces `claims = Depends(verify_service_jwt)`.
   - Derives `token_workspace_id = claims["workspace_id"]`.
   - Blocks cross-tenant mismatch with 403 Forbidden.
   - Queries SQL models strictly filtered by `workspace_id`.

---

## 5. Summary & Phase Execution Plan

- **Phase 1**: Secure configuration, remove fallback secrets, implement asymmetric RS256/EdDSA service tokens, update `.env.example`.
- **Phase 2**: Provision PostgreSQL + pgvector + Redis, migrate SQLAlchemy models, apply Postgres RLS.
- **Phase 3**: Consolidate RAG & commerce tools in Python with Pydantic schemas, true BM25, and real embeddings.
- **Phase 4**: Route all live chat & streaming through FastAPI with SSE.
- **Phase 5**: Delete duplicate TypeScript RAG/commerce logic.
- **Phase 6**: Enterprise quality, CI/CD, OpenTelemetry, TLS proxy.

---

## 6. Post-Migration Resolution Status

| Subsystem / Audit Item | Audit Gap Found (Phase 0) | Phase 6 Final Resolution |
| :--- | :--- | :--- |
| **Service Authentication** | Symmetric HS256 shared secret with default fallback strings. | Migrated to asymmetric **RS256** cryptographic keys (`SERVICE_JWT_PRIVATE_KEY` / `SERVICE_JWT_PUBLIC_KEY`). Next.js signs, FastAPI verifies with public key. |
| **Data Persistence** | Unversioned JSON files in `./data/`. | Migrated to **PostgreSQL 16 + pgvector** using SQLAlchemy 2.x and Alembic migrations. Multi-tenant Row-Level Security (`current_tenant_id`) active. |
| **RAG Retrieval** | Split between basic TS in-memory search and Python prototype. | Consolidated into **12-stage Python RAG pipeline** with Okapi BM25 scoring, HNSW vector indexing, prompt-injection defense boundaries, and `EmbeddingProvider` interface. |
| **Commerce Tools** | Duplicated across TypeScript and Python with divergent logic. | Consolidated into **10 Python Pydantic tools** in `python-backend/app/tools.py` with entity extraction, typo handling, stemming, and sorting. |
| **Live Chat Traffic** | Public `/api/v1/agents/[id]/chat` bypasses Python backend. | Live chat & SSE streaming routed directly through FastAPI (`POST /api/v1/agents/{id}/chat` & `/chat/stream`). Next.js functions strictly as UI and thin BFF proxy. |
| **Duplicate Code** | Duplicate `src/lib/rag` and `src/lib/commerce` in Next.js. | Duplicate TypeScript directories **deleted**. Zero business/commerce logic remains in Next.js. |
| **Observability & Probes** | Basic unredacted console logging. | Structured JSON logging with request IDs, trace correlation, automatic PII redaction (masking emails, phones, cards), `/healthz` and `/readyz` probes. |
| **Reverse Proxy & TLS** | Node.js was mapped directly to port 80 in Docker. | Nginx reverse proxy service added to `docker-compose.yml` routing `/api/v1/` to FastAPI and web to Next.js with TLS support. |
| **Test Verification** | Integration tests ran only in Node.js. | Automated Pytest suite (`27/27`), Production Acceptance suite (`33/33`), and Agentic Commerce Evaluation suite (`61/61`) all passing at 100%. |

