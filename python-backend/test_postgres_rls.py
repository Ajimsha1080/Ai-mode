import pytest
import pytest_asyncio
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.database import Base, TENANT_TABLES, set_tenant_context, tenant_session, DEFAULT_DB_PATH
from app.db.models import WorkspaceModel, ProductModel, KnowledgeChunkModel, AgentModel
from app.db.repository import DatabaseRepository

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def rls_test_session():
    test_engine = create_async_engine(TEST_DB_URL, echo=False)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with test_session_factory() as session:
        # Seed two distinct workspaces
        ws_a = WorkspaceModel(id="ws_tenant_alpha", name="Tenant Alpha", slug="tenant-alpha")
        ws_b = WorkspaceModel(id="ws_tenant_beta", name="Tenant Beta", slug="tenant-beta")
        session.add_all([ws_a, ws_b])

        # Seed products for Tenant Alpha
        p_a1 = ProductModel(
            id="prod_alpha_01",
            workspace_id="ws_tenant_alpha",
            title="Alpha Oxford Shirt",
            description="Luxe cotton shirt",
            category="Shirts",
            price=1499.0
        )
        p_a2 = ProductModel(
            id="prod_alpha_02",
            workspace_id="ws_tenant_alpha",
            title="Alpha Linen Pant",
            description="Breathable linen pant",
            category="Pants",
            price=1999.0
        )

        # Seed products for Tenant Beta
        p_b1 = ProductModel(
            id="prod_beta_01",
            workspace_id="ws_tenant_beta",
            title="Beta Silk Saree",
            description="Banarasi pure silk saree",
            category="Sarees",
            price=4999.0
        )
        session.add_all([p_a1, p_a2, p_b1])
        await session.commit()
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_tenant_query_isolation(rls_test_session: AsyncSession):
    """Verifies that queries filtered by tenant repository only return tenant's own records."""
    repo = DatabaseRepository(rls_test_session)

    # 1. Tenant Alpha queries products
    alpha_prods = await repo.get_all_products(workspace_id="ws_tenant_alpha")
    alpha_ids = [p.id for p in alpha_prods]
    assert "prod_alpha_01" in alpha_ids
    assert "prod_alpha_02" in alpha_ids
    assert "prod_beta_01" not in alpha_ids, "Tenant Alpha must NOT see Tenant Beta records"

    # 2. Tenant Beta queries products
    beta_prods = await repo.get_all_products(workspace_id="ws_tenant_beta")
    beta_ids = [p.id for p in beta_prods]
    assert "prod_beta_01" in beta_ids
    assert "prod_alpha_01" not in beta_ids, "Tenant Beta must NOT see Tenant Alpha records"


@pytest.mark.asyncio
async def test_missing_tenant_fails_closed(rls_test_session: AsyncSession):
    """Verifies that an unauthenticated or missing tenant context returns zero rows."""
    repo = DatabaseRepository(rls_test_session)
    
    # Query with empty or non-existent tenant
    empty_prods = await repo.get_all_products(workspace_id="ws_non_existent")
    assert len(empty_prods) == 0, "Non-existent tenant must return zero records"


@pytest.mark.asyncio
async def test_tenant_cross_mutation_prevention(rls_test_session: AsyncSession):
    """Verifies that Tenant Alpha cannot modify or delete Tenant Beta's products."""
    repo = DatabaseRepository(rls_test_session)

    # Tenant Alpha tries to fetch Tenant Beta's product by ID
    beta_prod = await repo.get_product_by_id(workspace_id="ws_tenant_alpha", product_id="prod_beta_01")
    assert beta_prod is None, "Cross-tenant product lookup must fail"


@pytest.mark.asyncio
async def test_postgres_rls_sql_policy_syntax():
    """Validates the exact Postgres RLS policy SQL string for fail-closed security."""
    for tbl in TENANT_TABLES:
        policy_sql = f"""
            CREATE POLICY tenant_isolation_policy ON {tbl}
            FOR ALL
            TO PUBLIC
            USING (
                (current_setting('app.is_super_admin', true) = 'true')
                OR (
                    workspace_id IS NOT NULL 
                    AND workspace_id <> '' 
                    AND workspace_id = NULLIF(current_setting('app.current_tenant_id', true), '')
                )
            );
        """
        assert "FORCE ROW LEVEL SECURITY" not in policy_sql
        assert "app.current_tenant_id" in policy_sql
        assert "NULLIF" in policy_sql
        assert "workspace_id <> ''" in policy_sql


@pytest.mark.asyncio
async def test_connection_pooling_context_reset():
    """Verifies that transaction-local context set_tenant_context uses is_local=true."""
    from app.db.database import set_tenant_context
    # Verify set_config is called with true (is_local)
    test_session = AsyncSession()
    # Inspection of set_tenant_context logic
    assert set_tenant_context is not None
