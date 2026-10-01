import os
import pytest
import asyncio
import time
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Test RS256 Keys
test_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_PEM = test_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode("utf-8")
PUBLIC_PEM = test_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode("utf-8")

os.environ["SERVICE_JWT_PUBLIC_KEY"] = PUBLIC_PEM
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_integration.db"
os.environ["APP_ENV"] = "development"

from app.db.database import init_db, async_session_factory
from app.db.repository import DatabaseRepository
from app.auth import verify_service_jwt, decode_token
from app.rag import execute_rag_pipeline, LocalDeterministicEmbeddingProvider
from app.tools import (
    search_products,
    get_inventory,
    lookup_order,
    coupon_validation,
    return_eligibility,
    create_return,
    add_to_cart,
    cart_lookup,
    human_handoff,
    execute_typed_tool
)
from app.agent_runtime import run_agent_cycle


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    asyncio.run(init_db())


@pytest.mark.asyncio
async def test_01_database_engine_and_seed_integrity():
    """Scenario 1: Database Engine & Seed Integrity."""
    async with async_session_factory() as session:
        repo = DatabaseRepository(session)
        products = await repo.get_all_products(workspace_id="ws_acme_corp")
        chunks = await repo.get_tenant_chunks(workspace_id="ws_acme_corp")
        
        assert len(products) >= 4, "Must have at least 4 products in seed data"
        assert len(chunks) >= 1, "Must have at least 1 knowledge chunk in seed data"
        
        # Verify product structure
        jacket = next((p for p in products if "jacket" in p.title.lower()), None)
        assert jacket is not None, "Seed data must contain a jacket"
        assert jacket.price > 0, "Product price must be greater than 0"
        assert jacket.workspace_id == "ws_acme_corp"


def test_02_authentication_and_jwt_rbac():
    """Scenario 2: Authentication, Hashing & JWT RBAC."""
    os.environ["SERVICE_JWT_PUBLIC_KEY"] = PUBLIC_PEM
    # Test valid RS256 service token
    token = jwt.encode(
        {
            "workspace_id": "ws_acme_corp",
            "sub": "service_node_01",
            "role": "ADMIN",
            "iss": "aaas-node",
            "aud": "aaas-python",
            "exp": int(time.time()) + 3600
        },
        PRIVATE_PEM,
        algorithm="RS256"
    )
    
    claims = verify_service_jwt(f"Bearer {token}")
    assert claims["workspace_id"] == "ws_acme_corp"
    assert claims["role"] == "ADMIN"
    
    # Test expired token rejection
    expired_token = jwt.encode(
        {
            "workspace_id": "ws_acme_corp",
            "sub": "service_node_01",
            "role": "ADMIN",
            "iss": "aaas-node",
            "aud": "aaas-python",
            "exp": int(time.time()) - 100
        },
        PRIVATE_PEM,
        algorithm="RS256"
    )
    with pytest.raises(Exception):
        verify_service_jwt(f"Bearer {expired_token}")


def test_03_rag_semantic_and_bm25_retrieval():
    """Scenario 3: RAG Semantic Chunking & Retrieval."""
    embedder = LocalDeterministicEmbeddingProvider()
    vec1 = embedder.embed_text("return and exchange policy within 7 days")
    vec2 = embedder.embed_text("how do I exchange an item for refund")
    vec3 = embedder.embed_text("electronics high definition sound amplifier")
    
    assert len(vec1) == 128
    
    # Cosine similarity
    import math
    def cosine_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    sim_high = cosine_sim(vec1, vec2)
    sim_low = cosine_sim(vec1, vec3)
    assert sim_high > sim_low, "Semantically similar policy queries must score higher"

    # Execution against tenant knowledge chunks
    res = execute_rag_pipeline(
        question="What is the return window?",
        workspace_id="ws_acme_corp",
        tenant_chunks=[{
            "chunk_id": "chk_01",
            "workspace_id": "ws_acme_corp",
            "doc_name": "Return Policy",
            "content": "Customers may return unworn items with tags within 30 days of delivery.",
            "embedding": vec1
        }]
    )
    assert len(res["citations"]) > 0
    assert res["grounding_verification"]["is_grounded"] is True


def test_04_commerce_engine_and_tool_execution():
    """Scenario 4: Commerce Engine & Tool Execution Engine."""
    # 1. Product search with budget constraint
    res_jacket = execute_typed_tool(
        "search_products",
        {"query": "jacket", "max_price": 3000.0},
        workspace_id="ws_acme_corp"
    )
    assert res_jacket["total_matches"] > 0
    assert all(p["price"] <= 3000.0 for p in res_jacket["products"])

    # 2. Search for non-existent category
    res_shoes = execute_typed_tool(
        "search_products",
        {"query": "shoes"},
        workspace_id="ws_acme_corp"
    )
    assert res_shoes["total_matches"] == 0
    assert len(res_shoes["products"]) == 0

    # 3. Order lookup with email matching
    res_order = execute_typed_tool(
        "order_lookup",
        {"order_number": "#10482", "customer_email": "sarah.connor@example.com"},
        workspace_id="ws_acme_corp"
    )
    assert res_order.get("found") is True
    assert res_order["order"]["order_number"] == "#10482"

    # 4. Coupon validation
    res_coupon = execute_typed_tool(
        "coupon_validation",
        {"code": "WELCOME10", "subtotal": 100.0},
        workspace_id="ws_acme_corp"
    )
    assert res_coupon["valid"] is True
    assert res_coupon["discount_amount"] > 0

    # 5. Return eligibility
    res_return = execute_typed_tool(
        "return_eligibility",
        {"order_number": "#10482", "customer_email": "sarah.connor@example.com"},
        workspace_id="ws_acme_corp"
    )
    assert res_return["order_number"] == "#10482"


def test_05_multi_step_agent_runtime_with_trace():
    """Scenario 5: Multi-Step Autonomous Agent Runtime with Trace Logging."""
    # A. Product query should return products
    prod_res = run_agent_cycle(
        agent_id="agent_shopmate_01",
        message="Show me Sunscreen Jackets",
        workspace_id="ws_acme_corp"
    )
    assert len(prod_res["response"]) > 0
    assert prod_res.get("interactive_payload") is not None
    assert prod_res["interactive_payload"]["type"] == "PRODUCTS"
    assert len(prod_res["interactive_payload"]["data"]) > 0

    # B. Non-existent item query must NOT attach product cards
    shoes_res = run_agent_cycle(
        agent_id="agent_shopmate_01",
        message="I want to buy running shoes and sneakers",
        workspace_id="ws_acme_corp"
    )
    assert len(shoes_res["response"]) > 0
    assert shoes_res.get("interactive_payload") is None or shoes_res["interactive_payload"]["data"] == []


def test_06_evaluations_and_grounding_suite():
    """Scenario 6: Automated Evaluations & Grounding Suite."""
    # Test grounded FAQ
    rag_eval = execute_rag_pipeline(
        question="How long do I have to return an item?",
        workspace_id="ws_acme_corp",
        tenant_chunks=[{
            "chunk_id": "chk_ret_01",
            "workspace_id": "ws_acme_corp",
            "doc_name": "Return Policy",
            "content": "All unworn items in original packaging can be returned within 30 days of receipt for a full refund.",
            "embedding": [0.05] * 128
        }]
    )
    assert rag_eval["grounding_verification"]["is_grounded"] is True
    assert len(rag_eval["citations"]) >= 1

    # Test empty workspace ungrounded check
    empty_eval = execute_rag_pipeline(
        question="What is the store warranty on electronics?",
        workspace_id="ws_empty_tenant",
        tenant_chunks=[]
    )
    assert len(empty_eval["citations"]) == 0
