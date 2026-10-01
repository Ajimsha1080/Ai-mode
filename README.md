# ShopMate AaaS — Enterprise Multi-Tenant E-Commerce AI Agent Platform

[![CI Quality, Security & Acceptance Suite](https://github.com/Ajimsha1080/Ai-mode/actions/workflows/ci.yml/badge.svg)](https://github.com/Ajimsha1080/Ai-mode/actions/workflows/ci.yml)
[![Next.js 15](https://img.shields.io/badge/Next.js-15.1.7-black?style=flat&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python_3.12-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16_pgvector-336791?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Redis 7](https://img.shields.io/badge/Redis-7_Alpine-DC382D?style=flat&logo=redis)](https://redis.io/)
[![Nginx](https://img.shields.io/badge/Nginx-TLS_Termination-009639?style=flat&logo=nginx)](https://nginx.org/)

A production-grade, hardened, multi-tenant enterprise **E-Commerce Agent-as-a-Service (AaaS)** platform. Built with a decoupled architecture featuring a **Next.js 15 UI and thin BFF proxy**, an asynchronous **Python 3.12 FastAPI backend of record** with a 12-stage Hybrid RAG pipeline (BM25 + pgvector HNSW), Postgres Row-Level Security (RLS), Redis distributed caching and rate-limiting, and an Nginx reverse proxy with TLS termination.

---

## 🏗️ Architecture Overview

```
                                  INTERNET / CLIENTS
                                          │
                                          ▼ HTTPS (443) / HTTP (80 -> 301)
                         ┌─────────────────────────────────┐
                         │      Nginx Reverse Proxy        │
                         │   - TLS 1.2+ Termination        │
                         │   - Security Headers (HSTS)     │
                         │   - SSE Streaming (Buffering Off)
                         └────────────────┬────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
   ┌─────────────────────────────┐                 ┌─────────────────────────────┐
   │    Next.js 15 Frontend      │                 │  Python 3.12 FastAPI Engine │
   │   (UI & Thin BFF Proxy)     │                 │     (Backend of Record)     │
   ├─────────────────────────────┤                 ├─────────────────────────────┤
   │ • Server Components & React │                 │ • 12-Stage Hybrid RAG       │
   │ • Asymmetric RS256 Signing  ├─(Service JWT)──►│ • Pydantic Typed Commerce   │
   │ • Session Cookie Forwarding │                 │ • LLM Multi-Provider Mesh   │
   │ • Zero Direct DB Access     │                 │ • Session Auth & Tokens     │
   └─────────────────────────────┘                 └──────────────┬──────────────┘
                                                                  │
                                           ┌──────────────────────┴──────────────────────┐
                                           ▼                                             ▼
                            ┌─────────────────────────────┐               ┌─────────────────────────────┐
                            │   PostgreSQL 16 + pgvector  │               │       Redis 7 Cache         │
                            │  - FORCE Row Level Security │               │  - Sliding Window Limits    │
                            │  - Dedicated app_user Role  │               │  - Distributed Lockout      │
                            │  - HNSW Vector Indexing     │               │  - Protected with Password  │
                            └─────────────────────────────┘               └─────────────────────────────┘
```

---

## 🔒 Security & Tenant Isolation

- **Postgres Row-Level Security (RLS)**: Enforced via `FORCE ROW LEVEL SECURITY` on all 18 tenant tables with non-superuser role `app_user`. Missing tenant context fails closed (0 rows returned).
- **Asymmetric Service Authentication**: Next.js signs service requests with an RS256 private key (`SERVICE_JWT_PRIVATE_KEY`); FastAPI verifies using the public key (`SERVICE_JWT_PUBLIC_KEY`).
- **Network Hardening**: Internal ports (Postgres `5432`, Redis `6379`, Python `8000`, Node `3000`) are not published to the host. Only Nginx reverse proxy publishes ports `80` and `443`.
- **Secrets Management**: No insecure default secret fallbacks. The application fails closed and refuses to boot if `SESSION_JWT_SECRET`, `SERVICE_JWT_PRIVATE_KEY`, or `ENCRYPTION_KEY` are missing or below 32 characters.
- **SSRF Defense**: Strict outbound fetch validation blocking cloud metadata services (`169.254.169.254`), private RFC 1918 subnets, and loopback evasions.

---

## 🚀 Quick Start with Docker Compose

### 1. Generate Cryptographic Keys & Secrets

Run the helper scripts to generate secure production secrets, RSA keypairs, and local TLS certificates:

```bash
# Generate high-entropy 32-character secrets (.env)
bash scripts/gen-secrets.sh

# Generate RS256 Keypair for Service JWT
bash scripts/gen-keypair.sh

# Generate TLS certificates for Nginx
bash scripts/gen-tls-certs.sh
```

### 2. Configure Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Ensure the following required environment variables are set in `.env`:

```env
APP_ENV=production
POSTGRES_DB=aaas_enterprise
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_strong_postgres_password
REDIS_PASSWORD=your_strong_redis_password
DATABASE_URL=postgresql+asyncpg://app_user:your_strong_app_user_password@postgres:5432/aaas_enterprise

# Asymmetric Service Authentication (RS256)
SERVICE_JWT_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
SERVICE_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"

# Session JWT Secret & Encryption Key (32+ chars)
SESSION_JWT_SECRET=your_32_character_long_session_secret!
ENCRYPTION_KEY=your_32_character_long_master_encryption_key!

# LLM Providers
SARVAM_API_KEY=your_sarvam_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 3. Build and Launch the Stack

```bash
docker compose up -d --build
```

Verify service status and healthchecks:

```bash
docker compose ps
```

The platform is accessible at:
- **HTTPS Storefront & Studio**: `https://localhost` (or `http://localhost` with automatic 301 HTTPS redirect)
- **API Health Endpoint**: `https://localhost/healthz`

---

## 🧪 Comprehensive Automated Test Suites

The repository contains end-to-end verification suites covering unit, integration, acceptance, and agentic evaluation criteria:

```bash
# 1. Run Python Backend Pytest Suite (36/36 tests: RLS, Auth, Parity, RAG, Connectors)
python -m pytest python-backend/ -v

# 2. Run TypeScript Acceptance Suite (33/33 tests: RBAC, SSRF, Fail-Closed Secrets)
npm run test:acceptance

# 3. Run Agentic E-Commerce Benchmark (61/61 tests: Multi-turn, Constraint Filtering, State)
npm run test:agentic

# 4. Next.js Typecheck & Production Build
npm run build
```

---

## 📄 Key Scripts Reference

| Script | Command | Purpose |
| :--- | :--- | :--- |
| **Acceptance Tests** | `npm run test:acceptance` | Validates multi-tenant isolation, SSRF prevention, secrets policy, and token validation. |
| **Agentic Tests** | `npm run test:agentic` | Benchmarks catalog search, multi-turn state inheritance, price sorting, and cart reasoning. |
| **Generate Secrets** | `bash scripts/gen-secrets.sh` | Generates 32-character high-entropy cryptographic keys for `.env`. |
| **Generate Keypair** | `bash scripts/gen-keypair.sh` | Generates 2048-bit RSA keypair for asymmetric service auth. |
| **Generate TLS Certs**| `bash scripts/gen-tls-certs.sh` | Creates self-signed TLS certificates for local Nginx testing. |

---

## 📜 License
MIT © 2026 ShopMate AaaS Platform Inc.
