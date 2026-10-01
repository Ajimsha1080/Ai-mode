"""Hardened Postgres RLS, fail-closed isolation policies, and non-superuser app_user role

Revision ID: 20261002_0002
Revises: 20261002_0001
Create Date: 2026-10-02 01:45:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = '20261002_0002'
down_revision: str | None = '20261002_0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = [
    "workspace_members", "agents", "agent_configs", "agent_versions",
    "agent_policies", "knowledge_sources", "knowledge_documents",
    "knowledge_chunks", "commerce_products", "commerce_orders",
    "commerce_carts", "conversations", "messages", "execution_traces",
    "deployments", "api_keys", "integrations", "audit_logs"
]

def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        # 1. Create dedicated non-superuser app_user role if not exists
        op.execute("""
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
        """)

        # Grant table and sequence permissions to app_user
        op.execute("GRANT USAGE ON SCHEMA public TO app_user;")
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;")
        op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;")
        op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;")
        op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;")

        # 2. Apply Strict Fail-Closed FORCE ROW LEVEL SECURITY and Policies
        for tbl in TENANT_TABLES:
            op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
            op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;")
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};")
            op.execute(f"""
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
            """)

def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        for tbl in TENANT_TABLES:
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};")
            op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY;")
            op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY;")
        op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM app_user;")
        op.execute("REVOKE USAGE ON SCHEMA public FROM app_user;")
