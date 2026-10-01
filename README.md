# ShopMate AaaS — Enterprise Multi-Tenant E-Commerce AI Agent Platform

[![Next.js 15](https://img.shields.io/badge/Next.js-15.1.7-black?style=flat&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python_3.12-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.0.0-blue?style=flat&logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue?style=flat&logo=typescript)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.x-38B2AC?style=flat&logo=tailwind-css)](https://tailwindcss.com/)
[![Sarvam AI](https://img.shields.io/badge/Sarvam_AI-105B_Conversations-orange?style=flat)](https://www.sarvam.ai/)
[![Acceptance Tests](https://img.shields.io/badge/Platform_Acceptance-33%2F33_Passing-brightgreen?style=flat)](scripts/test-acceptance.ts)
[![Agentic Commerce Tests](https://img.shields.io/badge/Agentic_Commerce-61%2F61_Passing-brightgreen?style=flat)](scripts/test-agentic-commerce.ts)
[![Integration Tests](https://img.shields.io/badge/Platform_Integration-6%2F6_Passing-brightgreen?style=flat)](scripts/test-integration.ts)

A production-grade, hardened, multi-tenant enterprise **E-Commerce Agent-as-a-Service (AaaS)** platform. Features a unified Next.js 15 full-stack frontend with visual shopping chat widgets and an asynchronous Python 3.12 FastAPI intelligence engine powered by a 12-Stage Hybrid RAG pipeline, authoritative structured catalog search, dynamic intent classification, conversational state memory, and multi-LLM orchestration (Sarvam AI 105B, OpenAI, Anthropic, Ollama).

---

## 🏗️ Agentic Commerce Architecture

```
                                  CUSTOMER
                                     │
                                     ▼
                    ┌───────────────────────────────────┐
                    │     AI Shopping Concierge         │
                    │   (Sarvam 105B / Next.js Runtime) │
                    └────────────────┬──────────────────┘
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│     Structured Commerce Engine│               │   12-Stage Store Knowledge RAG │
│  (AUTHORITATIVE SOURCE TRUTH) │               │   (POLICIES / FAQS / GUIDES)  │
├───────────────────────────────┤               ├───────────────────────────────┤
│ • Product IDs & SKUs          │               │ • Return & Refund Windows     │
│ • Real-time Pricing & MRP     │               │ • Shipping Rates & Delivery   │
│ • Live Variant Stock Levels   │               │ • Size Guides & Measurements  │
│ • Color & Occasion Mappings   │               │ • Brand FAQs & Contact Info   │
│ • Cart & Order State          │               │ • Material Care Instructions  │
└───────────────────────────────┘               └───────────────────────────────┘
           │                                                   │
           └─────────────────────────┬─────────────────────────┘
                                     │
                                     ▼
                    ┌───────────────────────────────────┐
                    │     Context & State Resolver      │
                    │  - Ordinals ("the second one")    │
                    │  - Pronouns ("is this in stock?") │
                    │  - Multi-Intent Query Unification │
                    └────────────────┬──────────────────┘
                                     │
                                     ▼
                    ┌───────────────────────────────────┐
                    │    Clean Natural Dialogue (Prose) │
                    │                +                  │
                    │  Interactive UI Visual Component  │
                    │ (PRODUCTS / CART / ORDER_TRACK)   │
                    └───────────────────────────────────┘
```

---

## 💎 Source-of-Truth Separation Rule

The platform strictly enforces the separation of product truth from conversational reasoning:

| Domain | Authoritative Provider | Role & Scope |
|---|---|---|
| **Product Discovery & Truth** | `LocalCommerceProvider` / `commerceEngine` | Product ID, SKU, title, category, price, discount, variant stock, images, product URLs. |
| **Inventory & Availability** | `commerceEngine.getInventory` | Real-time stock counts, size-specific variant stock verification. |
| **Cart Operations** | `commerceEngine.addToCart` / `removeFromCart` | Live basket calculation, subtotal, quantity updates, order line-items. |
| **Order Tracking** | `commerceEngine.getOrder` | Real-time shipment status, carrier tracking numbers, delivery addresses. |
| **Store Policies & FAQs** | 12-Stage Hybrid RAG Pipeline | Return/exchange windows, doorstep pickup terms, shipping times, brand info. |

---

## 🎯 General-Purpose Agentic Intent Routing

The agent dynamically determines customer intent without brittle hardcoding:

1. **Occasion & Semantic Discovery**:
   - *"Show me something good for a dinner"*
   - *"I need a gift for my brother under ₹1500"*
   - *"What would you recommend for a casual office day?"*
2. **Demographic & Attribute Filtering**:
   - *"Women's products"* (Strictly filters out male pieces, matches kurtas, sarees, dresses)
   - *"Any red shirts?"* (Resolves color families: `red`, `wine`, `maroon`, `crimson`)
3. **Multi-Product Comparison**:
   - *"Which one is cheaper?"*
   - *"Compare these two"* (Calculates price difference and styling suitability)
4. **Contextual Pronouns & Ordinals**:
   - *"Add the second one to my cart"*
   - *"Is this available in size M?"*
   - *"Show me something similar to the last product"*
5. **Live Inventory Inquiries**:
   - *"Is this in stock?"*
   - *"Do you have size M available?"* (Queries live variant database)
6. **Cart Actions**:
   - *"Add to cart"*
   - *"Remove that shirt"*
   - *"What is in my bag?"*
7. **Order Inquiries**:
   - *"Where is my order #10482?"* (Requires customer identifier, displays tracking carrier)
8. **Mixed Multi-Intent Support**:
   - *"Show me a black shirt under ₹2000 and tell me if I can return it."*
   - Concurrently executes structured product search + RAG policy lookup and provides a unified response.

---

## ✨ Core Platform Capabilities

### 1. 12-Stage Advanced Hybrid RAG Engine
- **Query Understanding & Entity Extraction**: Detects user intent and extracts parameters (size, color, price limits, ordinals).
- **Query Rewriting & Semantic Expansion**: Expands queries with domain-specific fashion synonyms.
- **Dense + Sparse Hybrid Search**: Combines high-dimensional semantic embeddings with BM25 keyword matching.
- **Reciprocal Rank Fusion (RRF)**: Merges retrieval candidate lists using RRF ($k=60$).
- **Cross-Encoder Scoring & Grounding Verification**: Verifies citations to guarantee factual confidence and prevent hallucinations.

### 2. Autonomous Multi-Page Store Crawler & Schema.org Ingestor
- **Automated Policy Discovery**: Scrapes policies across root `/`, `/pages/shipping-policy`, `/pages/return-exchange-policy`, `/pages/contact-us`, `/pages/about-us`, and `/pages/faq`.
- **Paginated Catalog Crawler**: Ingests up to 2,500 products per sync via `/products.json?limit=250&page=1..10`.
- **Schema.org JSON-LD Parser**: Automatically extracts `<script type="application/ld+json">` product entities from HTML.
- **Live Inventory Ingestion**: Imports pricing, compare-at MRPs, multi-variant stock levels, and high-res product photos.

### 3. Visual Interactive Chat & Instant Cart Management
- **Zero Fake Text Markers**: Complete elimination of fake markdown annotations like `[Product Card] ... — Add to Cart` from message prose.
- **Interactive Visual Cards**: High-res product cards with live stock badges, pricing, zoomable photo inspect modal, and instant 1-click **Add to Cart**.
- **Cart & Order Tracking**: Instant tracking lookup for active orders and real-time shopping bag calculations.

### 4. Enterprise Security, Privacy & Guardrails
- **Prompt Injection Boundaries**: All untrusted store catalog chunks are wrapped in `<<<UNTRUSTED_CATALOG_DATA>>>` delimiters to prevent prompt override attacks.
- **SSRF & Metadata Protection**: Strict `SafeFetch` utility blocking AWS/GCP cloud metadata IPs (`169.254.169.254`), RFC 1918 private subnets, IPv6 loopbacks, and hex/dword evasion.
- **Role-Based Access Control (RBAC)**: Tenant isolation across `OWNER`, `ADMIN`, `EDITOR`, and `VIEWER` roles.
- **Zero-Hallucination Safe Fallbacks**: Fails closed and avoids inventing policies when knowledge chunks are absent.

---

## 🚀 Quick Start & Local Setup

### Prerequisites
- Node.js 20+
- npm 10+
- Python 3.12+ (optional for local FastAPI service)

### 1. Environment Configuration
Create a `.env` file in the root directory (see `.env.example` for all required variables):

```env
APP_ENV=development
NODE_ENV=development

# LLM Configuration (Sarvam AI / OpenAI / Anthropic / Ollama)
SARVAM_API_KEY=your_sarvam_api_key_here
LLM_PROVIDER=sarvam
LLM_MODEL=sarvam-105b-conversations

# Backend Service URLs
PYTHON_BACKEND_URL=http://127.0.0.1:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Security Secrets (32+ chars - generate with bash scripts/gen-secrets.sh)
SESSION_JWT_SECRET=your_session_secret_at_least_32_chars_long
ENCRYPTION_KEY=your_encryption_key_at_least_32_chars_long
```

> **Note on Demo Accounts:** Demo merchant and admin accounts are only seeded automatically when `APP_ENV=dev` or `APP_ENV=development`. In production (`APP_ENV=production`), the application starts cleanly without default credentials.

### 2. Install Dependencies & Run
```bash
# Install Node packages
npm install

# Start Next.js development server
npm run dev
```

---

## 🧪 Comprehensive Verification & Test Suite

The repository includes comprehensive automated test suites:

```bash
# 1. Run Agentic Commerce Evaluation Suite (61/61 tests across 18+ scenarios)
npm run test:agentic

# 2. Run Platform Security & Multi-Tenancy Acceptance Suite (33/33 tests)
npm run test:acceptance

# 3. Run Platform Integration Suite (6/6 tests)
npm run test:integration

# 4. TypeScript Typecheck
npx tsc --noEmit

# 5. ESLint Check
npm run lint

# 6. Production Build Test
npm run build
```

---

## 🌐 Production Deployment (Docker Compose / EC2)

To deploy on AWS EC2 or any Linux VPS:

```bash
cd /var/www/AI-Native-Ecommerce
git fetch origin
git reset --hard origin/main
npm install
npm run build
pm2 restart all
```

Or via Docker Compose:

```bash
sudo docker compose up -d --build
```

---

## 📄 License
MIT © 2026 ShopMate AaaS Platform Inc.
