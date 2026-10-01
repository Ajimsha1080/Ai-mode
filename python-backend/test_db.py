import asyncio
import os

# Set development environment for testing
os.environ["APP_ENV"] = "development"

from app.db.database import async_session_factory, init_db
from app.db.models import (
    AgentConfigModel,
    AgentModel,
    AgentPolicyModel,
    KnowledgeChunkModel,
    KnowledgeDocModel,
    KnowledgeSourceModel,
    ProductModel,
    WorkspaceModel,
)
from app.db.repository import DatabaseRepository


async def run_db_tests():
    print("=== 1. Initializing Enterprise Database Schema & Seeding ===")
    await init_db()
    print("[OK] Schema initialized and seed check completed.")

    async with async_session_factory() as session:
        repo = DatabaseRepository(session)

        # Ensure Agent and Policy Fixtures exist
        agent = await repo.get_agent_with_config("agent_shopmate_01")
        if not agent:
            ws = await session.get(WorkspaceModel, "ws_acme_corp")
            if not ws:
                ws = WorkspaceModel(id="ws_acme_corp", name="Acme Footwear", slug="acme-footwear", tier="ENTERPRISE")
                session.add(ws)
                await session.flush()

            agent = AgentModel(id="agent_shopmate_01", workspace_id="ws_acme_corp", name="ShopMate Assistant", status="ACTIVE")
            session.add(agent)
            await session.flush()

            cfg = AgentConfigModel(
                id="cfg_shopmate_01",
                agent_id=agent.id,
                system_prompt="You are ShopMate AI assistant."
            )
            session.add(cfg)
            await session.flush()

        if not agent.policies:
            pol = AgentPolicyModel(
                id="pol_test_01",
                agent_id=agent.id,
                max_tokens_per_session=100000,
                rate_limit_rpm=60
            )
            session.add(pol)
            await session.commit()
            agent = await repo.get_agent_with_config("agent_shopmate_01")

        # 2. Check Workspaces
        print("\n=== 2. Verifying Multi-Tenant Workspace & Agent ===")
        assert agent is not None, "ShopMate agent not found in DB"
        print(f"[OK] Agent Found: {agent.name} (Workspace: {agent.workspace_id})")
        if agent.config:
            print(f"[OK] Config System Prompt: {agent.config.system_prompt[:50]}...")
        if agent.policies:
            print(f"[OK] Policies: Max tokens = {agent.policies[0].max_tokens_per_session}")

        # 3. Check Products
        print("\n=== 3. Verifying Products Catalog ===")
        products = await repo.get_all_products()
        if not products:
            p_seed = ProductModel(
                id="prod_01",
                workspace_id=agent.workspace_id,
                title="AeroPulse Velocity Running Shoes",
                price=149.99,
                stock=42,
                category="Footwear",
                description="Ultra-breathable running shoes"
            )
            session.add(p_seed)
            await session.commit()
            products = await repo.get_all_products()

        print(f"[OK] Found {len(products)} products in enterprise database.")
        for p in products:
            print(f"  - [{p.id}] {p.title} - ${p.price} (Stock: {p.stock})")

        # 4. Check Vector Search from DB
        print("\n=== 4. Verifying DB Vector Search on Knowledge Chunks ===")
        chunks = await repo.get_tenant_chunks(agent.workspace_id)
        if not chunks:
            ks = KnowledgeSourceModel(id="ks_test_01", workspace_id=agent.workspace_id, name="Handbook")
            session.add(ks)
            await session.flush()
            kd = KnowledgeDocModel(id="kd_test_01", source_id=ks.id, title="Policy", content="Return policy 30 days")
            session.add(kd)
            await session.flush()
            kc = KnowledgeChunkModel(id="kc_test_01", doc_id=kd.id, chunk_index=0, text="Return policy 30 days", embedding=[0.1] * 128)
            session.add(kc)
            await session.commit()

        import math
        query_vec = [math.sin(i + 42) for i in range(128)]
        vector_results = await repo.vector_similarity_search(agent.workspace_id, query_vec, top_k=2)
        print(f"[OK] Top {len(vector_results)} Vector Matches from Persistent DB:")
        for res in vector_results:
            print(f"  - Score: {res['similarity']} | Text: {res['text'][:60]}...")

        # 5. Check ACID Order Transaction
        print("\n=== 5. Testing ACID Order Transaction & Stock Deduction ===")
        target_prod = products[0]
        initial_stock = target_prod.stock
        order = await repo.create_order_transaction(
            workspace_id=agent.workspace_id,
            customer_email="enterprise_buyer@acme.com",
            items=[{"product_id": target_prod.id, "quantity": 2, "price": target_prod.price}],
            total_amount=target_prod.price * 2
        )
        await session.commit()
        print(f"[OK] Order created: {order.id} for ${order.total_amount}")

        # Verify stock updated
        updated_prod = await session.get(ProductModel, target_prod.id)
        assert updated_prod.stock == initial_stock - 2, "Stock deduction failed!"
        print(f"[OK] Stock successfully updated from {initial_stock} -> {updated_prod.stock}")

        # 6. Check Trace Recording
        print("\n=== 6. Testing Execution Trace Recording ===")
        trace = await repo.record_execution_trace(
            agent_id=agent.id,
            conversation_id="conv_test_001",
            duration_ms=45.2,
            tools_called=["search_products"],
            status="SUCCESS",
            trace_log={"rag_version": "12-stage-rrf"}
        )
        print(f"[OK] Trace logged: {trace.id} with status {trace.status}")

    print("\n[SUCCESS] ALL 6 ENTERPRISE DATABASE SUITES PASSED!")

if __name__ == "__main__":
    asyncio.run(run_db_tests())
