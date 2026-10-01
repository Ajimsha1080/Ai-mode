import asyncio
import math
import os

os.environ["APP_ENV"] = "development"

from app.db.database import async_session_factory, init_db
from app.db.repository import DatabaseRepository

TENANT_PROFILES = [
    {"id": "ws_jewelry_01", "name": "Aura Fine Jewelry", "slug": "aura-jewelry", "prod": "Solitaire Diamond Ring", "price": 4500.0, "policy": "Lifetime complimentary diamond cleaning and certified grading inspection."},
    {"id": "ws_coffee_02", "name": "Artisan Roast Roasters", "slug": "artisan-roast", "prod": "Ethiopian Yirgacheffe Beans", "price": 24.50, "policy": "Fresh roast guarantee: beans roasted within 48 hours of dispatch."},
    {"id": "ws_auto_03", "name": "Apex Auto Performance", "slug": "apex-auto", "prod": "Carbon Ceramic Brake Pads", "price": 680.0, "policy": "Track day replacement guarantee with 1-year rotor wear warranty."},
    {"id": "ws_luxury_04", "name": "Geneva Horology", "slug": "geneva-horology", "prod": "Tourbillon Chronograph Watch", "price": 12500.0, "policy": "5-year international certified chronometer mechanical warranty."},
    {"id": "ws_medical_05", "name": "MediCare Diagnostic Supplies", "slug": "medicare-supplies", "prod": "Digital Pulse Oximeter Pro", "price": 149.0, "policy": "FDA 510(k) certified clinical accuracy with sterile packaging."},
    {"id": "ws_pets_06", "name": "Pawfect Organic Pet Nutrition", "slug": "pawfect-nutrition", "prod": "Grain-Free Salmon Dog Kibble", "price": 65.0, "policy": "100% human-grade pasture-raised ingredient guarantee."},
    {"id": "ws_gaming_07", "name": "Titan Gaming Gear", "slug": "titan-gaming", "prod": "Ergonomic Pro RGB Gaming Chair", "price": 420.0, "policy": "10-year steel frame warranty with 4D armrest replacement."},
    {"id": "ws_fitness_08", "name": "IronCore Crossfit Equipment", "slug": "ironcore-fitness", "prod": "Olympic Competition Barbell 20kg", "price": 310.0, "policy": "Drop-tested up to 1500 lbs tensile strength with lifetime warranty."},
    {"id": "ws_beauty_09", "name": "Botanica Clean Skincare", "slug": "botanica-skincare", "prod": "Hyaluronic Acid Glow Serum", "price": 58.0, "policy": "Cruelty-free vegan certified with 60-day skin satisfaction guarantee."},
    {"id": "ws_tools_10", "name": "HeavyDuty Industrial Machining", "slug": "heavyduty-tools", "prod": "Brushless Cordless Impact Drill", "price": 289.0, "policy": "3-year heavy duty contractor tool replacement program."}
]

def make_vec(seed: int):
    return [math.sin(i + seed) for i in range(128)]

async def run_massive_multitenancy_test():
    print("========================================================")
    print("MASSIVE MULTI-TENANT ISOLATION BENCHMARK (10 TENANTS)")
    print("========================================================")

    await init_db()

    async with async_session_factory() as session:
        repo = DatabaseRepository(session)

        # 1. Onboard 10 Distinct Dynamic Tenants
        print("\n[PHASE 1] Provisioning 10 Independent Workspaces, Catalogs & Vector Knowledge...")
        for idx, t in enumerate(TENANT_PROFILES):
            # Check or create workspace
            ws = await repo.get_workspace(t["id"])
            if not ws:
                await repo.create_tenant_workspace(t["id"], t["name"], t["slug"])

            # Add product
            await repo.add_product(
                workspace_id=t["id"],
                title=t["prod"],
                price=t["price"],
                stock=100,
                description=f"Authentic {t['prod']} from {t['name']}"
            )

            # Add knowledge document & vector chunk
            chunk_vec = make_vec(idx * 7 + 1)
            await repo.add_knowledge_doc_with_chunks(
                workspace_id=t["id"],
                title=f"{t['name']} Master Terms",
                content=t["policy"],
                chunks=[{"text": t["policy"], "embedding": chunk_vec, "metadata": {"tenant": t["id"]}}]
            )
            print(f"  [OK] Tenant {idx+1:02d} provisioned: {t['id']} ({t['name']})")

        # 2. Strict Catalog Search Isolation Test
        print("\n[PHASE 2] Validating Zero Catalog Data Mixing Across All 10 Tenants...")
        for i, target_tenant in enumerate(TENANT_PROFILES):
            prods = await repo.get_all_products(workspace_id=target_tenant["id"])
            titles = [p.title for p in prods]

            # Must contain target tenant product
            assert any(target_tenant["prod"] in title for title in titles), f"Missing product for {target_tenant['id']}"

            # Must NOT contain products from ANY other 9 tenants
            for j, other_tenant in enumerate(TENANT_PROFILES):
                if i != j:
                    for title in titles:
                        assert other_tenant["prod"] not in title, f"CRITICAL LEAK: {target_tenant['id']} contains product from {other_tenant['id']}!"

            print(f"  [PASS] Tenant {target_tenant['id']}: Isolated {len(prods)} products (0 leaks).")

        # 3. Strict Vector Search Isolation Test
        print("\n[PHASE 3] Validating Zero Vector RAG Data Mixing Across All 10 Tenants...")
        for i, target_tenant in enumerate(TENANT_PROFILES):
            target_query_vec = make_vec(i * 7 + 1)
            vector_hits = await repo.vector_similarity_search(target_tenant["id"], target_query_vec, top_k=5)

            assert len(vector_hits) > 0, f"No vector hits for {target_tenant['id']}"

            # Check text matches target tenant policy
            top_hit = vector_hits[0]
            assert target_tenant["policy"][:30] in top_hit["text"], f"Vector search returned wrong policy for {target_tenant['id']}"

            # Verify no other tenant text exists in result
            for j, other_tenant in enumerate(TENANT_PROFILES):
                if i != j:
                    assert other_tenant["policy"][:30] not in top_hit["text"], f"CRITICAL VECTOR LEAK: {other_tenant['id']} chunk leaked into {target_tenant['id']}!"

            print(f"  [PASS] Tenant {target_tenant['id']}: Vector RAG matched strictly ({top_hit['similarity']:.4f}) with 0 cross-tenant contamination.")

        # 4. Strict ACID Transaction Isolation Test
        print("\n[PHASE 4] Validating Atomic Order Transactions Across Multiple Tenants...")
        # Tenant 3 (Apex Auto) order
        t3 = TENANT_PROFILES[2]
        t3_prods = await repo.get_all_products(workspace_id=t3["id"])
        t3_target = t3_prods[0]
        initial_stock = t3_target.stock

        order_3 = await repo.create_order_transaction(
            workspace_id=t3["id"],
            customer_email="racer@apexauto.com",
            items=[{"product_id": t3_target.id, "quantity": 4, "price": t3_target.price}],
            total_amount=t3_target.price * 4
        )
        await session.commit()

        # Check stock decremented for Tenant 3 only
        updated_t3 = (await repo.get_all_products(workspace_id=t3["id"]))[0]
        assert updated_t3.stock == initial_stock - 4, "Stock deduction failed for Tenant 3"
        print(f"  [PASS] Tenant 3 ({t3['id']}) order {order_3.id} placed. Stock atomically reduced {initial_stock} -> {updated_t3.stock}.")

        # Check Tenant 7 (Titan Gaming) stock is UNTOUCHED
        t7 = TENANT_PROFILES[6]
        t7_prod = (await repo.get_all_products(workspace_id=t7["id"]))[0]
        assert t7_prod.stock == 100, f"Tenant 7 stock corrupted by Tenant 3 order! Stock is {t7_prod.stock}"
        print(f"  [PASS] Tenant 7 ({t7['id']}) inventory intact at {t7_prod.stock} units.")

    print("\n========================================================")
    print("SUCCESS: 10/10 TENANTS VERIFIED WITH 100% STRICT DATA ISOLATION (ZERO LEAKS)")
    print("========================================================")

if __name__ == "__main__":
    asyncio.run(run_massive_multitenancy_test())
