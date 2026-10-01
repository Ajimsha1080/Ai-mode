import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import (
    WorkspaceModel, UserModel, WorkspaceMemberModel,
    AgentModel, AgentConfigModel, AgentPolicyModel,
    KnowledgeSourceModel, KnowledgeDocModel, KnowledgeChunkModel,
    ProductModel, OrderModel, ToolModel, IntegrationModel
)

def generate_embedding_128(text: str):
    import math, re
    dim = 128
    embedding = [0.0] * dim
    clean = re.sub(r'[^a-z0-9\s]', ' ', text.lower())
    words = [w for w in clean.split() if len(w) > 1]
    if not words:
        return embedding

    for i, word in enumerate(words):
        h = 0
        for char in word:
            h = (h * 31 + ord(char)) & 0xffffffff
        idx = abs(h) % dim
        weight = 1.0 + (0.5 if len(word) > 5 else 0.0)
        embedding[idx] += weight

        if i < len(words) - 1:
            next_word = words[i + 1]
            bh = 0
            for char in next_word:
                bh = (bh * 37 + ord(char)) & 0xffffffff
            b_idx = abs(bh) % dim
            embedding[b_idx] += 0.75

    norm = math.sqrt(sum(x * x for x in embedding))
    if norm > 0:
        embedding = [x / norm for x in embedding]
    return embedding

async def seed_database_if_empty(session: AsyncSession):
    """Checks if database has ws_acme_corp; if not, seeds standard multi-tenant datasets in dev mode."""
    import os
    app_env = (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "").lower()
    if app_env not in ("dev", "development"):
        # Never seed demo stores or users in production
        return

    stmt = select(ProductModel).where(ProductModel.workspace_id == "ws_acme_corp")
    res = await session.execute(stmt)
    if res.scalars().first():
        return

    # =========================================================================
    # TENANT A: Blue Tyga Store (ws_acme_corp)
    # =========================================================================
    ws_acme = WorkspaceModel(
        id="ws_acme_corp",
        name="Blue Tyga Store",
        slug="blue-tyga-store",
        tier="GROWTH"
    )
    session.add(ws_acme)

    user_acme = UserModel(
        id="usr_acme_admin",
        email="admin@bluetyga.com",
        name="Blue Tyga Store Admin",
        role="ADMIN"
    )
    session.add(user_acme)

    session.add(WorkspaceMemberModel(
        id="wsm_acme_01",
        workspace_id=ws_acme.id,
        user_id=user_acme.id,
        role="OWNER"
    ))

    agent_acme = AgentModel(
        id="agent_shopmate_01",
        workspace_id=ws_acme.id,
        name="Blue Tyga AI Concierge",
        description="Official shopping and support agent for Blue Tyga Techwear.",
        status="ACTIVE"
    )
    session.add(agent_acme)

    session.add(AgentConfigModel(
        id="cfg_acme_01",
        agent_id=agent_acme.id,
        model="sarvam-105b-conversations",
        temperature=0.3,
        system_prompt="You are the Blue Tyga AI Shopping Concierge. Help shoppers discover techwear apparel, check orders, and explain return policies.",
        tools_enabled=["search_products", "check_inventory", "calculate_cart", "apply_discount", "lookup_order"],
        rag_enabled=True
    ))

    # Blue Tyga Products
    acme_prods = [
        ProductModel(
            id="prod_01",
            workspace_id=ws_acme.id,
            title="UPF 50+ Sunscreen Performance Jacket",
            price=2499.00,
            stock=42,
            category="Outerwear",
            description="Ultra-lightweight UV-blocking techwear jacket with quick-dry cooling mesh."
        ),
        ProductModel(
            id="prod_02",
            workspace_id=ws_acme.id,
            title="No-Sweat Anti-Odour Tech Tee",
            price=999.00,
            stock=55,
            category="T-Shirts",
            description="Seamless breathable bamboo-elastane blend with silver-ion antimicrobial finish."
        ),
        ProductModel(
            id="prod_03",
            workspace_id=ws_acme.id,
            title="All-Day 4-Way Stretch Commuter Joggers",
            price=1899.00,
            stock=30,
            category="Bottoms",
            description="Water-repellent 4-way stretch joggers with zippered concealed security pockets."
        )
    ]
    session.add_all(acme_prods)

    # Blue Tyga Orders
    session.add(OrderModel(
        id="ord_acme_10482",
        workspace_id=ws_acme.id,
        customer_email="sarah.connor@example.com",
        total_amount=2499.00,
        currency="INR",
        status="DELIVERED",
        items_json=[{"order_number": "#10482", "carrier": "Bluedart Express", "tracking_number": "BD-8941039821-IN", "items": ["1x UPF 50+ Sunscreen Performance Jacket (Size L)"], "shipping_address": "Indiranagar, Bengaluru, KA 560038"}]
    ))

    # Blue Tyga Knowledge Base
    ks_acme = KnowledgeSourceModel(id="ks_acme_01", workspace_id=ws_acme.id, name="Blue Tyga Policy Handbook", type="HANDBOOK")
    session.add(ks_acme)

    doc_acme_1 = KnowledgeDocModel(
        id="doc_acme_ret",
        source_id=ks_acme.id,
        title="Blue Tyga 7-Day Exchange & Warranty Policy.pdf",
        content="Blue Tyga Policy:\n1. 7-day hassle-free size exchanges and returns for unworn items with tags.\n2. Defective or damaged items are covered with instant free replacement."
    )
    doc_acme_2 = KnowledgeDocModel(
        id="doc_acme_ship",
        source_id=ks_acme.id,
        title="Shipping, Prepaid Discounts & Pan-India Delivery.md",
        content="Free express shipping on all prepaid orders across India via Bluedart and Delhivery. Standard delivery takes 2 to 4 business days."
    )
    session.add_all([doc_acme_1, doc_acme_2])

    chunks_acme = [
        KnowledgeChunkModel(
            id="chk_acme_01",
            doc_id=doc_acme_1.id,
            chunk_index=0,
            text="Blue Tyga Return & Exchange Policy: Hassle-free 7-day exchange window for sizing and fit. Products must be unused with original tags intact.",
            embedding=generate_embedding_128("Blue Tyga Return & Exchange Policy: Hassle-free 7-day exchange window for sizing and fit. Products must be unused with original tags intact.")
        ),
        KnowledgeChunkModel(
            id="chk_acme_02",
            doc_id=doc_acme_1.id,
            chunk_index=1,
            text="Shipping Policy: Free express delivery across India for all prepaid orders above Rs 499. Cash on Delivery (COD) available with a nominal Rs 49 handling fee.",
            embedding=generate_embedding_128("Shipping Policy: Free express delivery across India for all prepaid orders above Rs 499. Cash on Delivery available.")
        )
    ]
    session.add_all(chunks_acme)

    # =========================================================================
    # TENANT B: TechNova Electronics (ws_tech_store)
    # =========================================================================
    ws_tech = WorkspaceModel(
        id="ws_tech_store",
        name="TechNova Electronics",
        slug="technova-store",
        tier="ENTERPRISE"
    )
    session.add(ws_tech)

    user_tech = UserModel(
        id="usr_tech_admin",
        email="admin@technova.com",
        name="TechNova Admin",
        role="ADMIN"
    )
    session.add(user_tech)

    session.add(WorkspaceMemberModel(
        id="wsm_tech_01",
        workspace_id=ws_tech.id,
        user_id=user_tech.id,
        role="OWNER"
    ))

    agent_tech = AgentModel(
        id="agent_tech_01",
        workspace_id=ws_tech.id,
        name="TechNova Hardware Expert",
        description="Specialist in computing, gadgets, and technical warranty policies.",
        status="ACTIVE"
    )
    session.add(agent_tech)

    session.add(AgentConfigModel(
        id="cfg_tech_01",
        agent_id=agent_tech.id,
        model="claude-3-5-sonnet",
        temperature=0.3,
        system_prompt="You are the TechNova Hardware AI Assistant.",
        tools_enabled=["search_products", "check_inventory", "calculate_cart", "apply_discount", "lookup_order"],
        rag_enabled=True
    ))

    # TechNova Products
    tech_prods = [
        ProductModel(
            id="prod_tech_01",
            workspace_id=ws_tech.id,
            title="UltraBook Titanium 16 M3 Pro",
            price=2199.00,
            stock=12,
            category="Laptops",
            description="M3 Pro architecture with 32GB RAM, 1TB SSD, 120Hz Liquid Retina display."
        ),
        ProductModel(
            id="prod_tech_02",
            workspace_id=ws_tech.id,
            title="Chronos Smartwatch Gen 4",
            price=399.00,
            stock=25,
            category="Wearables",
            description="Sapphire glass, ECG monitoring, titanium bezel, 14-day battery reserve."
        )
    ]
    session.add_all(tech_prods)

    # TechNova Orders
    session.add(OrderModel(
        id="ord_tech_20991",
        workspace_id=ws_tech.id,
        customer_email="buyer@technova.com",
        total_amount=2199.00,
        currency="USD",
        status="IN_TRANSIT",
        items_json=[{"order_number": "#20991", "carrier": "UPS Next Day Air", "tracking_number": "1Z9999999999999999", "items": ["1x UltraBook Titanium 16"], "shipping_address": "100 Market St, San Francisco, CA"}]
    ))

    # TechNova Knowledge Base
    ks_tech = KnowledgeSourceModel(id="ks_tech_01", workspace_id=ws_tech.id, name="TechNova Warranty Documents", type="HANDBOOK")
    session.add(ks_tech)

    doc_tech_1 = KnowledgeDocModel(
        id="doc_tech_war",
        source_id=ks_tech.id,
        title="TechNova 2-Year Hardware Replacement & AppleCare Equivalent.pdf",
        content="TechNova Electronics Policy: All certified laptops and smartwatches come with a 2-Year Instant Replacement Warranty covering battery degradation and screen failure. Returns on opened electronics are subject to a 14-day return window and 0% restocking fee when reset to factory settings."
    )
    session.add(doc_tech_1)

    chunk_tech_1 = KnowledgeChunkModel(
        id="chk_tech_01",
        doc_id=doc_tech_1.id,
        chunk_index=0,
        text="TechNova Electronics Policy: All certified laptops and smartwatches come with a 2-Year Instant Replacement Warranty covering battery degradation and screen failure. Returns on opened electronics are subject to a 14-day return window and 0% restocking fee when reset to factory settings.",
        embedding=generate_embedding_128("TechNova Electronics Policy: All certified laptops and smartwatches come with a 2-Year Instant Replacement Warranty covering battery degradation and screen failure.")
    )
    session.add(chunk_tech_1)

    await session.commit()
