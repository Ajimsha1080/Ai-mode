#!/usr/bin/env python3
"""
One-Off Seed Data Import Script for PostgreSQL / SQLite Database.
Migrates all seed records (workspaces, users, agents, configs, products, orders, knowledge, tools)
into SQLAlchemy tables with proper tenant isolation (workspace_id) and embeddings.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add python-backend to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "python-backend"))

from app.db.database import engine, async_session_factory, init_db, Base
from app.db.models import (
    WorkspaceModel, UserModel, WorkspaceMemberModel,
    AgentModel, AgentConfigModel, AgentVersionModel, AgentPolicyModel,
    KnowledgeSourceModel, KnowledgeDocModel, KnowledgeChunkModel,
    ProductModel, OrderModel, CartModel, ToolModel, DeploymentModel, ApiKeyModel
)
from app.db.seed import generate_embedding_128

BLUE_TYGA_PRODUCTS = [
    {
        "id": "prod_bt_01",
        "title": "Sunscreen Jacket",
        "description": "Engineered UPF 50+ UV-blocking lightweight breathable jacket designed for daily outdoor sun protection.",
        "category": "Outerwear",
        "tags": ["jacket", "sunscreen", "upf50", "uvwear", "outerwear", "men"],
        "price": 999.00,
        "compare_at_price": 1999.00,
        "currency": "INR",
        "images": ["https://cdn.shopify.com/s/files/1/0446/5629/6087/files/SJ1-1-100.webp?v=1776246748"],
        "in_stock": True,
        "total_inventory": 65,
        "variants": [
            {"id": "var_bt01_m", "title": "Medium / Obsidian Black", "sku": "BT-SJ-M-BLK", "price": 999.00, "inventory_quantity": 30, "attributes": {"size": "M", "color": "Black"}},
            {"id": "var_bt01_l", "title": "Large / Obsidian Black", "sku": "BT-SJ-L-BLK", "price": 999.00, "inventory_quantity": 35, "attributes": {"size": "L", "color": "Black"}}
        ]
    },
    {
        "id": "prod_bt_02",
        "title": "Sunscreen Jacket Pro",
        "description": "High-performance UPF 50+ technical sunscreen jacket with utility zippered pockets, cooling mesh, and active flex.",
        "category": "Outerwear",
        "tags": ["jacket", "pro", "sunscreen", "upf50", "outerwear"],
        "price": 1299.00,
        "compare_at_price": 2999.00,
        "currency": "INR",
        "images": ["https://cdn.shopify.com/s/files/1/0446/5629/6087/files/SJ2_-_1_4a769590-ab42-4c42-bc68-874df3032dc8.webp?v=1776246852"],
        "in_stock": True,
        "total_inventory": 50,
        "variants": [
            {"id": "var_bt02_m", "title": "Medium / Navy Blue", "sku": "BT-SJP-M-NVY", "price": 1299.00, "inventory_quantity": 25, "attributes": {"size": "M", "color": "Navy"}},
            {"id": "var_bt02_l", "title": "Large / Navy Blue", "sku": "BT-SJP-L-NVY", "price": 1299.00, "inventory_quantity": 25, "attributes": {"size": "L", "color": "Navy"}}
        ]
    },
    {
        "id": "prod_bt_03",
        "title": "Sunscreen Jacket Ice Pro",
        "description": "Next-gen cooling techwear jacket with Arctic Ice cool-touch heat dispersal and certified UPF 50+ rating.",
        "category": "Outerwear",
        "tags": ["jacket", "ice", "cooling", "upf50", "outerwear", "ice pro"],
        "price": 1999.00,
        "compare_at_price": 3999.00,
        "currency": "INR",
        "images": ["https://cdn.shopify.com/s/files/1/0446/5629/6087/files/BTF.webp?v=1779275127"],
        "in_stock": True,
        "total_inventory": 45,
        "variants": [
            {"id": "var_bt03_m", "title": "Medium / Arctic Ice Grey", "sku": "BT-ICE-M-GRY", "price": 1999.00, "inventory_quantity": 20, "attributes": {"size": "M", "color": "Ice Grey"}},
            {"id": "var_bt03_l", "title": "Large / Arctic Ice Grey", "sku": "BT-ICE-L-GRY", "price": 1999.00, "inventory_quantity": 25, "attributes": {"size": "L", "color": "Ice Grey"}}
        ]
    },
    {
        "id": "prod_bt_04",
        "title": "Women Sunscreen Jacket Ice Pro",
        "description": "Tailored women ergonomic UPF 50+ cooling jacket with thumbholes, ponytail aperture, and ice-filament fabric.",
        "category": "Outerwear",
        "tags": ["women", "jacket", "ice pro", "sunscreen", "upf50"],
        "price": 1999.00,
        "compare_at_price": 3999.00,
        "currency": "INR",
        "images": ["https://cdn.shopify.com/s/files/1/0446/5629/6087/files/WOMENLSJ8-1_2x-100.webp?v=1772778127"],
        "in_stock": True,
        "total_inventory": 40,
        "variants": [
            {"id": "var_bt04_s", "title": "Small / Lavender Ice", "sku": "BT-WICE-S-LAV", "price": 1999.00, "inventory_quantity": 20, "attributes": {"size": "S", "color": "Lavender"}},
            {"id": "var_bt04_m", "title": "Medium / Lavender Ice", "sku": "BT-WICE-M-LAV", "price": 1999.00, "inventory_quantity": 20, "attributes": {"size": "M", "color": "Lavender"}}
        ]
    },
    {
        "id": "prod_bt_05",
        "title": "Anti-AC Thermal Jacket 2 Pro",
        "description": "Dual-layer thermal fleece insulation engineered for air-conditioned corporate spaces and chill protection without bulk.",
        "category": "Hoodies",
        "tags": ["thermal", "anti-ac", "jacket", "hoodie", "outerwear"],
        "price": 1799.00,
        "compare_at_price": 4999.00,
        "currency": "INR",
        "images": ["https://cdn.shopify.com/s/files/1/0446/5629/6087/files/ANTI_AC_PRO_1-100.jpg?v=1762598400"],
        "in_stock": True,
        "total_inventory": 40,
        "variants": [
            {"id": "var_bt05_m", "title": "Medium / Stealth Black", "sku": "BT-AC2-M-BLK", "price": 1799.00, "inventory_quantity": 20, "attributes": {"size": "M", "color": "Black"}},
            {"id": "var_bt05_l", "title": "Large / Stealth Black", "sku": "BT-AC2-L-BLK", "price": 1799.00, "inventory_quantity": 20, "attributes": {"size": "L", "color": "Black"}}
        ]
    },
    {
        "id": "prod_bt_06",
        "title": "No Sweat Tech Tee",
        "description": "Quick-dry moisture-wicking engineered active tee designed to stay cool, fresh, and odor-free all day.",
        "category": "T-Shirts",
        "tags": ["tshirt", "nosweat", "quick-dry", "activewear", "tee"],
        "price": 799.00,
        "compare_at_price": 1499.00,
        "currency": "INR",
        "images": ["https://cdn.shopify.com/s/files/1/0446/5629/6087/files/NoSweatTee_1.webp?v=1777871708"],
        "in_stock": True,
        "total_inventory": 80,
        "variants": [
            {"id": "var_bt06_m", "title": "Medium / Olive Green", "sku": "BT-NST-M-OLV", "price": 799.00, "inventory_quantity": 40, "attributes": {"size": "M", "color": "Olive"}},
            {"id": "var_bt06_l", "title": "Large / Olive Green", "sku": "BT-NST-L-OLV", "price": 799.00, "inventory_quantity": 40, "attributes": {"size": "L", "color": "Olive"}}
        ]
    },
    {
        "id": "prod_shirt_cord_nvy",
        "title": "Corduroy Shirt: Navy",
        "description": "Luxe fine-wale corduroy button-down shirt designed for casual styling and evening dinner occasions.",
        "category": "Shirts",
        "tags": ["shirt", "corduroy", "men", "navy", "casual", "dinner", "apparel"],
        "price": 1499.00,
        "currency": "INR",
        "images": ["https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=600&auto=format&fit=crop&q=80"],
        "in_stock": True,
        "total_inventory": 40,
        "variants": [
            {"id": "var_sc_nvy_m", "title": "Medium / Navy", "sku": "CS-NVY-M", "price": 1499.00, "inventory_quantity": 20, "attributes": {"size": "M", "color": "Navy"}},
            {"id": "var_sc_nvy_l", "title": "Large / Navy", "sku": "CS-NVY-L", "price": 1499.00, "inventory_quantity": 20, "attributes": {"size": "L", "color": "Navy"}}
        ]
    },
    {
        "id": "prod_kurta_mandala",
        "title": "Mandala Elephant Embroidered Kurta",
        "description": "Intricate royal mandala elephant embroidery on pure silk blend fabric for festive occasions and weddings.",
        "category": "Kurtas",
        "tags": ["kurta", "ethnic", "women", "festive", "wedding", "mandala", "embroidered", "apparel"],
        "price": 1699.00,
        "currency": "INR",
        "images": ["https://images.unsplash.com/photo-1609357605129-26f69add5d6e?w=600&auto=format&fit=crop&q=80"],
        "in_stock": True,
        "total_inventory": 45,
        "variants": [
            {"id": "var_km_m", "title": "Medium / Teal Blue", "sku": "KM-M", "price": 1699.00, "inventory_quantity": 20, "attributes": {"size": "M", "color": "Teal"}},
            {"id": "var_km_l", "title": "Large / Teal Blue", "sku": "KM-L", "price": 1699.00, "inventory_quantity": 25, "attributes": {"size": "L", "color": "Teal"}}
        ]
    },
    {
        "id": "prod_saree_yellow_floral",
        "title": "Yellow Floral Saree",
        "description": "Hand-block printed yellow floral pure georgette saree with scalloped golden border.",
        "category": "Sarees",
        "tags": ["saree", "ethnic", "women", "yellow floral", "yellow", "festive", "wedding", "apparel"],
        "price": 1699.00,
        "currency": "INR",
        "images": ["https://images.unsplash.com/photo-1610030469668-935cb17fa6b8?w=600&auto=format&fit=crop&q=80"],
        "in_stock": True,
        "total_inventory": 30,
        "variants": [
            {"id": "var_syf_uni", "title": "Free Size / Yellow", "sku": "SYF-UNI", "price": 1699.00, "inventory_quantity": 30, "attributes": {"size": "Free Size", "color": "Yellow"}}
        ]
    }
]

BLUE_TYGA_ORDERS = [
    {
        "id": "ord_10482",
        "order_number": "#10482",
        "customer_email": "sarah.sharma@gmail.com",
        "total_amount": 2499.00,
        "currency": "INR",
        "status": "DELIVERED",
        "carrier": "Bluedart Express",
        "tracking_number": "BD-8941039821-IN",
        "masked_address": "Indiranagar, 12th Main, Bengaluru, KA 560038",
        "items_json": [
            {"product_id": "prod_bt_01", "title": "UPF 50+ Sunscreen Performance Jacket (Large / Obsidian Black)", "quantity": 1, "price": 2499.00}
        ]
    },
    {
        "id": "ord_10490",
        "order_number": "#10490",
        "customer_email": "rahul.verma@gmail.com",
        "total_amount": 1899.00,
        "currency": "INR",
        "status": "SHIPPED",
        "carrier": "Delhivery Surface",
        "tracking_number": "DEL-104908912-IN",
        "masked_address": "Koramangala 4th Block, Bengaluru, KA 560034",
        "items_json": [
            {"product_id": "prod_bt_03", "title": "All-Day 4-Way Stretch Commuter Joggers (Size 32 / Slate Grey)", "quantity": 1, "price": 1899.00}
        ]
    }
]

STANDARD_TOOLS = [
    {"id": "search_products", "name": "search_products", "category": "CATALOG", "description": "Search store catalog by keyword, category, price range, color, or attributes.", "risk_level": "READ_ONLY"},
    {"id": "get_inventory", "name": "get_inventory", "category": "CATALOG", "description": "Check real-time stock levels for a specific product and size/color variant.", "risk_level": "READ_ONLY"},
    {"id": "order_lookup", "name": "order_lookup", "category": "ORDER", "description": "Retrieve status, line items, and delivery info for an order number.", "risk_level": "READ_ONLY"},
    {"id": "order_tracking", "name": "order_tracking", "category": "ORDER", "description": "Retrieve real-time carrier tracking status and estimated delivery time.", "risk_level": "READ_ONLY"},
    {"id": "cart_lookup", "name": "cart_lookup", "category": "CART", "description": "View current active cart items, subtotal, discounts, and estimated total.", "risk_level": "READ_ONLY"},
    {"id": "add_to_cart", "name": "add_to_cart", "category": "CART", "description": "Add an in-stock product item or variant to the shopping cart.", "risk_level": "WRITE_SAFE"},
    {"id": "coupon_validation", "name": "coupon_validation", "category": "CART", "description": "Validate and calculate discount for a promotional promo code.", "risk_level": "READ_ONLY"},
    {"id": "return_eligibility", "name": "return_eligibility", "category": "ORDER", "description": "Verify if an order item meets the return policy and conditions.", "risk_level": "READ_ONLY"},
    {"id": "create_return", "name": "create_return", "category": "ORDER", "description": "Initiate a return request and generate a return shipping label.", "risk_level": "FINANCIAL"},
    {"id": "human_handoff", "name": "human_handoff", "category": "SUPPORT", "description": "Escalate the conversation to a human support representative.", "risk_level": "READ_ONLY"}
]

async def migrate_seed_data(force: bool = False):
    print("=" * 65)
    print("MIGRATING SEED DATA TO DATABASE OF RECORD")
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'Default SQLite/PostgreSQL')}")
    print("=" * 65)

    # 1. Initialize DB schema, RLS policies & vector indices
    if force:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    else:
        await init_db()

    async with async_session_factory() as session:
        from sqlalchemy import select

        # Check existing data
        stmt = select(WorkspaceModel).where(WorkspaceModel.id == "ws_acme_corp")
        res = await session.execute(stmt)
        existing_ws = res.scalars().first()

        if existing_ws and not force:
            print("[OK] Database already seeded with 'ws_acme_corp'. Skipping duplicate import.")
            return

        print("\n1. Seeding Workspaces & Users...")
        ws_acme = WorkspaceModel(
            id="ws_acme_corp",
            name="Blue Tyga Store",
            slug="blue-tyga-store",
            tier="GROWTH",
            plan="GROWTH",
            settings_json={"retention_days": 90, "security": {"rate_limit_rpm": 120, "allowed_origins": ["*"]}}
        )
        ws_tech = WorkspaceModel(
            id="ws_tech_store",
            name="TechNova Electronics",
            slug="technova-electronics",
            tier="ENTERPRISE",
            plan="ENTERPRISE",
            settings_json={"retention_days": 365, "security": {"rate_limit_rpm": 300, "allowed_origins": ["*"]}}
        )
        session.add_all([ws_acme, ws_tech])

        user_merchant = UserModel(
            id="usr_merchant_01",
            email="merchant@shopmate.com",
            name="Alex Vance (Store Owner)",
            role="ADMIN"
        )
        user_admin = UserModel(
            id="usr_admin_01",
            email="admin@aaas-platform.com",
            name="Platform SuperAdmin",
            role="SUPERADMIN",
            is_super_admin=True
        )
        session.add_all([user_merchant, user_admin])

        session.add_all([
            WorkspaceMemberModel(id="wsm_acme_01", workspace_id=ws_acme.id, user_id=user_merchant.id, role="OWNER"),
            WorkspaceMemberModel(id="wsm_tech_01", workspace_id=ws_tech.id, user_id=user_admin.id, role="OWNER")
        ])
        await session.flush()

        print("2. Seeding AI Agents, Configurations & Guardrails...")
        agent_acme = AgentModel(
            id="agent_shopmate_01",
            workspace_id=ws_acme.id,
            name="Blue Tyga AI Concierge",
            description="Official shopping and support agent for Blue Tyga Techwear.",
            status="ACTIVE"
        )
        session.add(agent_acme)

        cfg_acme = AgentConfigModel(
            id="cfg_acme_01",
            workspace_id=ws_acme.id,
            agent_id=agent_acme.id,
            model="sarvam-105b-conversations",
            temperature=0.3,
            system_prompt="You are the Blue Tyga AI Shopping Concierge. Help shoppers discover techwear apparel, check orders, and explain return policies.",
            tools_enabled=["search_products", "get_inventory", "cart_lookup", "add_to_cart", "coupon_validation", "order_lookup", "order_tracking", "return_eligibility", "create_return", "human_handoff"],
            rag_enabled=True,
            identity_json={"name": "ShopMate", "brand_name": "Blue Tyga"}
        )
        session.add(cfg_acme)

        agent_tech = AgentModel(
            id="agent_tech_01",
            workspace_id=ws_tech.id,
            name="TechNova Support Concierge",
            description="AI assistant for TechNova high-performance electronics.",
            status="ACTIVE"
        )
        session.add(agent_tech)

        cfg_tech = AgentConfigModel(
            id="cfg_tech_01",
            workspace_id=ws_tech.id,
            agent_id=agent_tech.id,
            model="gpt-4o-mini",
            temperature=0.2,
            system_prompt="You are the TechNova Electronics Concierge. Assist customers with tech specs, inventory, and instant replacement warranty queries.",
            tools_enabled=["search_products", "get_inventory", "order_lookup", "order_tracking"],
            rag_enabled=True,
            identity_json={"name": "NovaAI", "brand_name": "TechNova"}
        )
        session.add(cfg_tech)
        await session.flush()

        print("3. Seeding Product Catalogs & Variants...")
        for p in BLUE_TYGA_PRODUCTS:
            searchable = f"{p['title']} {p.get('category', '')} {' '.join(p.get('tags', []))} {p.get('description', '')}".lower()
            prod_obj = ProductModel(
                id=p["id"],
                workspace_id=ws_acme.id,
                title=p["title"],
                description=p.get("description", ""),
                category=p.get("category", "Apparel"),
                tags=p.get("tags", []),
                price=float(p["price"]),
                compare_at_price=float(p.get("compare_at_price", 0)) if p.get("compare_at_price") else None,
                currency=p.get("currency", "INR"),
                images=p.get("images", []),
                in_stock=p.get("in_stock", True),
                total_inventory=int(p.get("total_inventory", 50)),
                source_url=p.get("source_url", f"https://bluetyga.com/products/{p['id']}"),
                searchable_text=searchable,
                embedding=generate_embedding_128(searchable),
                variants_json=p.get("variants", [])
            )
            session.add(prod_obj)

        tech_prods = [
            {
                "id": "prod_tech_01",
                "title": "UltraBook Titanium 16 M3 Pro",
                "category": "Laptops",
                "price": 2199.00,
                "currency": "USD",
                "total_inventory": 12,
                "description": "M3 Pro architecture with 32GB RAM, 1TB SSD, 120Hz Liquid Retina display."
            },
            {
                "id": "prod_tech_02",
                "title": "Chronos Smartwatch Gen 4",
                "category": "Wearables",
                "price": 399.00,
                "currency": "USD",
                "total_inventory": 25,
                "description": "Sapphire glass, ECG monitoring, titanium bezel, 14-day battery reserve."
            }
        ]
        for p in tech_prods:
            searchable = f"{p['title']} {p.get('category', '')} {p.get('description', '')}".lower()
            session.add(ProductModel(
                id=p["id"],
                workspace_id=ws_tech.id,
                title=p["title"],
                description=p.get("description", ""),
                category=p.get("category", "Electronics"),
                tags=["electronics", p.get("category", "").lower()],
                price=float(p["price"]),
                currency=p.get("currency", "USD"),
                in_stock=True,
                total_inventory=p["total_inventory"],
                searchable_text=searchable,
                embedding=generate_embedding_128(searchable),
                variants_json=[]
            ))
        await session.flush()

        print("4. Seeding Knowledge Bases & RAG Vector Chunks...")
        ks_acme = KnowledgeSourceModel(id="ks_acme_01", workspace_id=ws_acme.id, name="Blue Tyga Policies & FAQ", type="POLICY_MANUAL")
        session.add(ks_acme)
        await session.flush()

        doc_acme_1 = KnowledgeDocModel(
            id="doc_acme_ret",
            workspace_id=ws_acme.id,
            source_id=ks_acme.id,
            title="Blue Tyga 30-Day Return & Doorstep Exchange Policy.pdf",
            content="Blue Tyga Return & Exchange Terms:\n1. 30-Day Return Window: Customers may initiate a return or size exchange within 30 days of shipment delivery for all unworn apparel with tags attached.\n2. Free Doorstep Pickup: Pre-paid Bluedart return labels and doorstep courier pickups are scheduled automatically across 19,000+ PIN codes.\n3. Defective / Damaged items receive instant 100% full refunds or replacement units without return shipping fees."
        )
        session.add(doc_acme_1)
        await session.flush()

        chunk_acme_1 = KnowledgeChunkModel(
            id="chk_acme_01",
            workspace_id=ws_acme.id,
            doc_id=doc_acme_1.id,
            chunk_index=0,
            text="Blue Tyga 30-Day Return & Doorstep Exchange Policy: Customers may return or exchange unworn apparel with original tags within 30 days of delivery. Free doorstep pickup is provided via Bluedart.",
            embedding=generate_embedding_128("Blue Tyga 30-Day Return & Doorstep Exchange Policy: Customers may return or exchange unworn apparel with original tags within 30 days of delivery.")
        )
        session.add(chunk_acme_1)
        await session.flush()

        print("5. Seeding Orders, Tools & Deployments...")
        for ord_data in BLUE_TYGA_ORDERS:
            session.add(OrderModel(
                id=ord_data["id"],
                workspace_id=ws_acme.id,
                order_number=ord_data.get("order_number", ord_data["id"]),
                customer_email=ord_data["customer_email"],
                total_amount=float(ord_data["total_amount"]),
                currency=ord_data.get("currency", "INR"),
                status=ord_data.get("status", "DELIVERED"),
                carrier=ord_data.get("carrier", "Bluedart Express"),
                tracking_number=ord_data.get("tracking_number", "BD-8941039821-IN"),
                masked_address=ord_data.get("masked_address", ""),
                items_json=ord_data.get("items_json", []),
                timeline_json=[]
            ))

        for t in STANDARD_TOOLS:
            session.add(ToolModel(
                id=f"{ws_acme.id}_{t['id']}",
                workspace_id=ws_acme.id,
                name=t["name"],
                category=t["category"],
                description=t["description"],
                risk_level=t["risk_level"],
                is_enabled=True
            ))

        dep_acme = DeploymentModel(
            id="dep_acme_live",
            workspace_id=ws_acme.id,
            agent_id=agent_acme.id,
            name="Blue Tyga Live Storefront Widget",
            public_key="pk_live_bt_99214481023",
            allowed_domains=["*"],
            status="ACTIVE"
        )
        session.add(dep_acme)

        await session.commit()
        print("\n========================================================")
        print("[OK] ALL SEED DATA SUCCESSFULLY MIGRATED TO DATABASE!")
        print("========================================================")

if __name__ == "__main__":
    asyncio.run(migrate_seed_data(force="--force" in sys.argv))
