import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

# Base declarative class
class Base(DeclarativeBase):
    pass

# Resolve Database URL
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "aaas_enterprise.db"

raw_db_url = os.getenv("DATABASE_URL", "")

if not raw_db_url:
    DATABASE_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH.as_posix()}"
else:
    # Normalize postgresql driver to asyncpg
    if raw_db_url.startswith("postgres://"):
        DATABASE_URL = raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw_db_url.startswith("postgresql://") and not raw_db_url.startswith("postgresql+asyncpg://"):
        DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif raw_db_url.startswith("sqlite://") and not raw_db_url.startswith("sqlite+aiosqlite://"):
        DATABASE_URL = raw_db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    else:
        DATABASE_URL = raw_db_url

# Engine options
engine_kwargs: dict[str, Any] = {
    "echo": False,
    "future": True,
}

if "sqlite" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_recycle"] = 3600

# SQLite high performance PRAGMAs
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass

engine = create_async_engine(DATABASE_URL, **engine_kwargs)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# ==============================================================================
# POSTGRES ROW-LEVEL SECURITY & TENANT SESSION MANAGEMENT
# ==============================================================================

TENANT_TABLES = [
    "workspace_members",
    "agents",
    "agent_configs",
    "agent_versions",
    "agent_policies",
    "knowledge_sources",
    "knowledge_documents",
    "knowledge_chunks",
    "commerce_products",
    "commerce_orders",
    "commerce_carts",
    "conversations",
    "messages",
    "execution_traces",
    "deployments",
    "api_keys",
    "integrations",
    "audit_logs"
]

async def set_tenant_context(session: AsyncSession, workspace_id: str | None = None, is_super_admin: bool = False):
    """Sets PostgreSQL transaction-local configuration for Row-Level Security."""
    if "postgresql" in DATABASE_URL:
        # Transaction-scoped (is_local=true). Clears automatically on commit or rollback.
        tid_val = str(workspace_id) if workspace_id else ""
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
            {"tid": tid_val}
        )
        await session.execute(
            text("SELECT set_config('app.is_super_admin', :isa, true)"),
            {"isa": "true" if is_super_admin else "false"}
        )

@asynccontextmanager
async def tenant_session(workspace_id: str | None = None, is_super_admin: bool = False) -> AsyncGenerator[AsyncSession, None]:
    """Provides a scoped async session with enforced Postgres Row-Level Security."""
    async with async_session_factory() as session:
        await set_tenant_context(session, workspace_id=workspace_id, is_super_admin=is_super_admin)
        try:
            yield session
        finally:
            pass

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injector for general FastAPI endpoints"""
    async with async_session_factory() as session:
        yield session

async def apply_postgres_rls_and_vector_indices(conn):
    """Enables pgvector extension, non-superuser app_user permissions, hardened fail-closed RLS policies, and HNSW indexes."""
    if "postgresql" in DATABASE_URL:
        # 1. Enable pgvector extension
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception:
            pass

        # 2. Create app_user non-superuser role and grant privileges
        try:
            await conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
                        CREATE ROLE app_user WITH LOGIN PASSWORD 'app_user_secure_production_password_32char!'
                        NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
                    ELSE
                        ALTER ROLE app_user WITH NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
                    END IF;
                END
                $$;
            """))
            await conn.execute(text("GRANT USAGE ON SCHEMA public TO app_user;"))
            await conn.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;"))
            await conn.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;"))
        except Exception:
            pass

        # 3. Enable Strict Fail-Closed FORCE Row-Level Security on all tenant-owned tables
        for tbl in TENANT_TABLES:
            try:
                await conn.execute(text(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;"))
                await conn.execute(text(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;"))
                await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};"))
                await conn.execute(text(f"""
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
                    )
                    WITH CHECK (
                        (current_setting('app.is_super_admin', true) = 'true')
                        OR (
                            workspace_id IS NOT NULL
                            AND workspace_id <> ''
                            AND workspace_id = NULLIF(current_setting('app.current_tenant_id', true), '')
                        )
                    );
                """))
            except Exception:
                pass

        # 4. Create HNSW Vector Index for fast approximate cosine similarity
        try:
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding_hnsw
                ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_commerce_products_embedding_hnsw
                ON commerce_products USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """))
        except Exception:
            pass

async def init_db():
    """Initializes database schema, pgvector extensions, RLS policies, and seeds dev data."""
    from .seed import seed_database_if_empty

    async with engine.begin() as conn:
        if "postgresql" in DATABASE_URL:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception:
                pass
        await conn.run_sync(Base.metadata.create_all)
        await apply_postgres_rls_and_vector_indices(conn)

    # Run dev seeding if applicable
    async with async_session_factory() as session:
        await seed_database_if_empty(session)
