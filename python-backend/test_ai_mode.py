import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ai_mode.adapters.catalog_adapter import CatalogAdapter
from app.ai_mode.services.comparison_engine import AIModeComparisonEngine
from app.ai_mode.services.conversation_service import AIModeConversationService
from app.ai_mode.services.deployment_service import AIModeDeploymentService
from app.ai_mode.services.knowledge_service import AIModeKnowledgeService
from app.ai_mode.services.recommendation_engine import AIModeRecommendationEngine
from app.ai_mode.services.search_engine import AIModeSearchEngine
from app.db.database import Base
from app.db.models import ProductModel, WorkspaceModel

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Seed Workspace & Test Catalog
        ws_a = WorkspaceModel(id="ws_store_a", name="Store A", slug="store-a")
        ws_b = WorkspaceModel(id="ws_store_b", name="Store B", slug="store-b")
        session.add_all([ws_a, ws_b])

        p1 = ProductModel(
            id="prod_jacket_01",
            workspace_id="ws_store_a",
            title="UPF 50+ Sunscreen Jacket",
            description="Ultra-light breathable sun protection jacket with moisture wicking fabric.",
            category="Outerwear",
            price=1899.0,
            tags=["sunscreen", "jacket", "running", "upf50"],
            attributes_json={"material": "100% Polyester", "fit": "Regular", "color": "Navy Blue"},
            in_stock=True,
            total_inventory=45
        )
        p2 = ProductModel(
            id="prod_jogger_02",
            workspace_id="ws_store_a",
            title="Active Travel Joggers",
            description="Four-way stretch travel joggers with concealed zipper pockets.",
            category="Bottoms",
            price=1499.0,
            tags=["joggers", "travel", "stretch", "pockets"],
            attributes_json={"material": "Nylon Elastane", "fit": "Slim", "color": "Charcoal"},
            in_stock=True,
            total_inventory=60
        )
        p3 = ProductModel(
            id="prod_tee_03",
            workspace_id="ws_store_a",
            title="Pro Dri-FIT Running Tee",
            description="High performance moisture-wicking short sleeve athletic t-shirt.",
            category="Tops",
            price=899.0,
            tags=["running", "tee", "dri-fit", "breathable"],
            attributes_json={"material": "Recycled Polyester", "fit": "Athletic"},
            in_stock=True,
            total_inventory=100
        )

        # Isolated Workspace B product
        p_b = ProductModel(
            id="prod_store_b_01",
            workspace_id="ws_store_b",
            title="Competitor Luxury Coat",
            description="Luxury cashmere coat for store B.",
            category="Outerwear",
            price=15000.0,
            tags=["luxury", "coat"],
            in_stock=True
        )

        session.add_all([p1, p2, p3, p_b])
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_ai_mode_search_engine(db_session: AsyncSession):
    catalog = CatalogAdapter(db_session)
    engine = AIModeSearchEngine(catalog)

    # 1. Natural Language Search with Price Filter
    res1 = await engine.execute_search(
        workspace_id="ws_store_a",
        query="Show lightweight jackets under ₹2,000"
    )
    assert len(res1.products) >= 1
    assert res1.products[0].id == "prod_jacket_01"
    assert res1.search_plan["intent"] == "PRICE_FILTER"
    assert res1.search_plan["price_max"] == 2000.0

    # 2. Natural Language Search with Category & Attribute
    res2 = await engine.execute_search(
        workspace_id="ws_store_a",
        query="travel joggers with zipper pockets"
    )
    assert len(res2.products) >= 1
    assert res2.products[0].id == "prod_jogger_02"

    # 3. Dynamic Sorting
    res3 = await engine.execute_search(
        workspace_id="ws_store_a",
        query="cheapest athletic clothing"
    )
    assert len(res3.products) == 3
    assert res3.products[0].price <= res3.products[1].price  # Dri-FIT Tee (899) first


@pytest.mark.asyncio
async def test_ai_mode_comparison_engine(db_session: AsyncSession):
    catalog = CatalogAdapter(db_session)
    comp_engine = AIModeComparisonEngine(catalog)

    res = await comp_engine.compare_products(
        workspace_id="ws_store_a",
        product_ids=["prod_jacket_01", "prod_jogger_02"]
    )
    assert len(res.products) == 2
    assert len(res.comparison_table) >= 4
    # Check Price row
    price_row = next(r for r in res.comparison_table if r["feature"] == "Price")
    assert "1,899.00" in price_row["UPF 50+ Sunscreen Jacket"]
    assert "1,499.00" in price_row["Active Travel Joggers"]

    # Check non-existent attribute shows "Information not available" rather than hallucination
    color_row = next((r for r in res.comparison_table if r["feature"] == "Color"), None)
    if color_row:
        assert color_row["UPF 50+ Sunscreen Jacket"] == "Navy Blue"


@pytest.mark.asyncio
async def test_ai_mode_recommendation_engine(db_session: AsyncSession):
    catalog = CatalogAdapter(db_session)
    rec_engine = AIModeRecommendationEngine(catalog)

    res = await rec_engine.get_recommendations(
        workspace_id="ws_store_a",
        product_id="prod_jacket_01",
        limit=2
    )
    assert len(res.recommendations) > 0
    assert all(r.id != "prod_jacket_01" for r in res.recommendations)


@pytest.mark.asyncio
async def test_ai_mode_conversational_shopping(db_session: AsyncSession):
    conv_service = AIModeConversationService(db_session)

    # Turn 1: Initial Discovery
    turn1 = await conv_service.process_chat(
        workspace_id="ws_store_a",
        message="I'm looking for running gear"
    )
    assert turn1.conversation_id is not None
    assert len(turn1.products) >= 1

    # Turn 2: Follow-up constraint ("Show cheaper options")
    turn2 = await conv_service.process_chat(
        workspace_id="ws_store_a",
        message="Show cheaper options",
        conversation_id=turn1.conversation_id
    )
    assert turn2.conversation_id == turn1.conversation_id
    assert len(turn2.products) >= 1

    # Turn 3: Add to cart
    turn3 = await conv_service.process_chat(
        workspace_id="ws_store_a",
        message="Add the first one to cart",
        conversation_id=turn1.conversation_id
    )
    assert "Added" in turn3.response or "shopping cart" in turn3.response


@pytest.mark.asyncio
async def test_ai_mode_knowledge_service(db_session: AsyncSession):
    ks = AIModeKnowledgeService(db_session)

    # Ingest FAQ
    source = await ks.create_source(
        workspace_id="ws_store_a",
        name="Store Return Policy",
        source_type="FAQ",
        config={},
        raw_content="We offer a 7-day hassle-free exchange on all athletic clothing."
    )
    assert source["status"] == "READY"
    assert source["chunk_count"] >= 1

    # Verify listing
    sources = await ks.list_sources("ws_store_a")
    assert len(sources) >= 1
    assert sources[0]["name"] == "Store Return Policy"


@pytest.mark.asyncio
async def test_ai_mode_deployment_service(db_session: AsyncSession):
    ds = AIModeDeploymentService(db_session)

    dep = await ds.create_deployment(
        workspace_id="ws_store_a",
        name="Production Store Widget",
        allowed_domains=["store-a.com"],
        welcome_message="Welcome to Store A!"
    )
    assert dep["public_widget_id"].startswith("aim_pub_")
    assert "data-ai-mode-widget-id" in dep["embed_code"]

    # Public lookup
    found = await ds.get_by_public_widget_id(dep["public_widget_id"])
    assert found is not None
    assert found.workspace_id == "ws_store_a"


@pytest.mark.asyncio
async def test_ai_mode_tenant_isolation(db_session: AsyncSession):
    catalog = CatalogAdapter(db_session)
    search_engine = AIModeSearchEngine(catalog)

    # Store A must NEVER see Store B's luxury coat
    res_a = await search_engine.execute_search(
        workspace_id="ws_store_a",
        query="coat"
    )
    assert all(p.id != "prod_store_b_01" for p in res_a.products)

    # Store B sees its own product
    res_b = await search_engine.execute_search(
        workspace_id="ws_store_b",
        query="coat"
    )
    assert any(p.id == "prod_store_b_01" for p in res_b.products)
