import os
import sys
import pytest
import asyncio
from typing import Dict, Any

from app.db.database import init_db
from app.rag import (
    EmbeddingProvider,
    LocalDeterministicEmbeddingProvider,
    OpenAIEmbeddingProvider,
    OllamaEmbeddingProvider,
    get_embedding_provider,
    BM25Retriever,
    execute_rag_pipeline,
    generate_embedding,
    cosine_similarity
)
from app.tools import (
    search_products,
    get_inventory,
    order_lookup,
    order_tracking,
    coupon_validation,
    return_eligibility,
    create_return,
    add_to_cart,
    cart_lookup,
    human_handoff,
    execute_typed_tool,
    parse_search_query,
    stem_word,
    TYPO_MAP,
    SearchProductsInput,
    GetInventoryInput,
    OrderLookupInput
)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    os.environ["APP_ENV"] = "development"
    asyncio.run(init_db())


# ============================================================================
# 1. EMBEDDING PROVIDER & BM25 TESTS
# ============================================================================

def test_embedding_provider_interface():
    local_prov = LocalDeterministicEmbeddingProvider(dim=128)
    assert local_prov.dimension == 128
    vec = local_prov.embed_text("Sunscreen Performance Jacket")
    assert len(vec) == 128
    assert math_norm(vec) > 0.99

    batch = local_prov.embed_batch(["Jacket 1", "Jacket 2"])
    assert len(batch) == 2
    assert len(batch[0]) == 128

def math_norm(vec):
    import math
    return math.sqrt(sum(x*x for x in vec))

def test_bm25_retriever():
    corpus = [
        "Blue Tyga Return & Exchange Policy: 30-day exchange window for unworn apparel with tags.",
        "Shipping Policy: Free express delivery across India via Bluedart and Delhivery.",
        "TechNova 2-Year Instant Replacement Warranty for laptops and smartwatches."
    ]
    bm25 = BM25Retriever(corpus)
    scores = bm25.score("return policy and exchange window")
    assert len(scores) == 3
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


# ============================================================================
# 2. NLP ENTITY & CONSTRAINT EXTRACTION TESTS
# ============================================================================

def test_stemmer_and_typo_correction():
    assert stem_word("shirts") == "shirt"
    assert stem_word("jackets") == "jacket"
    assert stem_word("panties") == "panty"
    assert stem_word("dresses") == "dress"

    assert "wmoen" in TYPO_MAP
    assert TYPO_MAP["wmoen"] == "women"
    assert TYPO_MAP["shrit"] == "shirt"
    assert TYPO_MAP["trak"] == "track"

def test_parse_search_query_constraints():
    schema = {
        "categories": ["Outerwear", "Shirts", "T-Shirts", "Kurtas", "Sarees"],
        "tags": ["jacket", "sunscreen", "cotton", "bamboo"],
        "attribute_values": {"color": ["black", "navy", "green", "yellow"], "size": ["s", "m", "l", "xl"]}
    }

    parsed = parse_search_query("Show women shirts under ₹1500 in size M", schema)
    assert parsed["gender"] == "women"
    assert parsed["explicit_category"] == "Shirts"
    assert parsed["max_price"] == 1500.0
    assert parsed["size"] == "M"

    parsed_sort = parse_search_query("Show cheaper jackets", schema)
    assert parsed_sort["sort"] == "price_asc"


# ============================================================================
# 3. MULTI-TURN SEARCH STATE INHERITANCE & PAGINATION
# ============================================================================

def test_multi_turn_state_inheritance():
    schema = {
        "categories": ["Shirts", "Outerwear"],
        "tags": ["cotton", "casual"],
        "attribute_values": {}
    }

    turn1_state = {
        "explicitCategory": "Shirts",
        "gender": "men",
        "maxPrice": 2000.0,
        "page": 1,
        "pageSize": 6,
        "original_query": "men shirts under 2000"
    }

    # Turn 2: User says "show more" (pagination)
    parsed_turn2 = parse_search_query("show more", schema, last_search_state=turn1_state)
    assert parsed_turn2["scope"] == "pagination"
    assert parsed_turn2["page"] == 2
    assert parsed_turn2["explicit_category"] == "Shirts"
    assert parsed_turn2["gender"] == "men"
    assert parsed_turn2["max_price"] == 2000.0


# ============================================================================
# 4. PRODUCT SEARCH TOOL & CONSTRAINTS (BLUE TYGA TENANT)
# ============================================================================

def test_search_products_tool_constraints():
    # 1. Search jackets
    res_jackets = search_products(workspace_id="ws_acme_corp", query="jackets")
    assert res_jackets["total_matches"] > 0
    assert any("jacket" in p["title"].lower() for p in res_jackets["products"])

    # 2. Strict category constraint: shirts
    res_shirts = search_products(workspace_id="ws_acme_corp", query="men shirts")
    assert res_shirts["total_matches"] > 0
    for p in res_shirts["products"]:
        assert p["category"] == "Shirts"

    # 3. Non-existent entity constraint (e.g. shoes in apparel store)
    res_shoes = search_products(workspace_id="ws_acme_corp", query="running shoes")
    assert res_shoes["total_matches"] == 0
    assert len(res_shoes["products"]) == 0

    # 4. Deterministic Pagination
    res_page1 = search_products(workspace_id="ws_acme_corp", query="shirts", page=1, page_size=3)
    assert res_page1["page"] == 1
    assert len(res_page1["products"]) == 3
    assert res_page1["has_more"] is True

    res_page2 = search_products(workspace_id="ws_acme_corp", query="shirts", page=2, page_size=3)
    assert res_page2["page"] == 2
    assert len(res_page2["products"]) > 0
    # Zero duplicates across pages
    page1_ids = {p["id"] for p in res_page1["products"]}
    page2_ids = {p["id"] for p in res_page2["products"]}
    assert page1_ids.isdisjoint(page2_ids)


# ============================================================================
# 5. ALL 10 COMMERCE TOOLS WITH SCHEMAS
# ============================================================================

def test_tool_get_inventory():
    res = get_inventory(workspace_id="ws_acme_corp", product_id="prod_01")
    assert res["in_stock"] is True
    assert res["stock_count"] > 0
    assert "UPF 50+" in res["title"]

def test_tool_order_lookup_and_tracking():
    # Matching email
    res_lookup = order_lookup(workspace_id="ws_acme_corp", order_number="#10482", customer_email="sarah.connor@example.com")
    assert res_lookup["found"] is True
    assert res_lookup["order"]["status"] == "DELIVERED"

    # Mismatched email -> fails closed (prevents enumeration)
    res_bad = order_lookup(workspace_id="ws_acme_corp", order_number="#10482", customer_email="attacker@evil.com")
    assert res_bad["found"] is False

    # Tracking
    res_track = order_tracking(workspace_id="ws_acme_corp", order_number="#10482", customer_email="sarah.connor@example.com")
    assert res_track["found"] is True
    assert "Bluedart" in res_track["carrier"]

def test_tool_coupon_validation():
    res_val = coupon_validation(workspace_id="ws_acme_corp", coupon_code="WELCOME10", cart_subtotal=1000.0)
    assert res_val["valid"] is True
    assert res_val["discount_amount"] == 100.0

    res_invalid = coupon_validation(workspace_id="ws_acme_corp", coupon_code="FAKE_CODE", cart_subtotal=1000.0)
    assert res_invalid["valid"] is False

def test_tool_return_and_exchange():
    res_elig = return_eligibility(workspace_id="ws_acme_corp", order_number="#10482")
    assert res_elig["eligible"] is True
    assert res_elig["return_window_days"] == 30

    res_create = create_return(workspace_id="ws_acme_corp", order_number="#10482", customer_email="sarah.connor@example.com", reason="Size exchange")
    assert res_create["success"] is True
    assert res_create["return_id"].startswith("ret_")

def test_tool_cart_actions():
    res_add = add_to_cart(workspace_id="ws_acme_corp", product_id="prod_01", quantity=2)
    assert res_add["success"] is True
    assert res_add["quantity"] == 2

    res_calc = cart_lookup(
        workspace_id="ws_acme_corp",
        items=[{"product_id": "prod_01", "quantity": 1}],
        discount_code="WELCOME10"
    )
    assert res_calc["subtotal"] > 0
    assert res_calc["discount_amount"] > 0
    assert res_calc["grand_total"] > 0

def test_tool_human_handoff():
    res_handoff = human_handoff(workspace_id="ws_acme_corp", reason="Complex custom alteration request")
    assert res_handoff["status"] == "ESCALATED"
    assert res_handoff["ticket_id"].startswith("tkt_")


# ============================================================================
# 6. TENANT ISOLATION (BLUE TYGA VS TECHNOVA)
# ============================================================================

def test_multi_tenant_isolation_tools_and_rag():
    # Blue Tyga searches should never return TechNova items
    bt_res = search_products(workspace_id="ws_acme_corp", query="laptops")
    assert bt_res["total_matches"] == 0

    # TechNova searches should return laptops
    tech_res = search_products(workspace_id="ws_tech_store", query="laptops")
    assert tech_res["total_matches"] > 0
    assert "UltraBook" in tech_res["products"][0]["title"]

    # RAG: Blue Tyga returns Blue Tyga policy, TechNova returns TechNova warranty
    bt_rag = execute_rag_pipeline(question="What is your return policy?", workspace_id="ws_acme_corp")
    assert "Blue Tyga" in bt_rag["natural_answer"]

    tech_rag = execute_rag_pipeline(question="What is the warranty policy?", workspace_id="ws_tech_store")
    assert "TechNova" in tech_rag["natural_answer"]
