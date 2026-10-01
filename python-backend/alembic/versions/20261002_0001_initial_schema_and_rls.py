"""Initial schema, pgvector HNSW indices, and Postgres Row-Level Security

Revision ID: 20261002_0001
Revises:
Create Date: 2026-10-02 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

revision: str = '20261002_0001'
down_revision: str | None = None
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
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. Workspaces
    op.create_table(
        'workspaces',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), unique=True, nullable=False),
        sa.Column('tier', sa.String(50), server_default="GROWTH"),
        sa.Column('plan', sa.String(50), server_default="GROWTH"),
        sa.Column('settings_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 2. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('role', sa.String(50), server_default="MEMBER"),
        sa.Column('is_super_admin', sa.Boolean(), server_default="false"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 3. Workspace Members
    op.create_table(
        'workspace_members',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(64), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), server_default="OWNER"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 4. Agents
    op.create_table(
        'agents',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), server_default="ACTIVE"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 5. Agent Configs
    op.create_table(
        'agent_configs',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(64), sa.ForeignKey('agents.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('model', sa.String(100), server_default="sarvam-105b-conversations"),
        sa.Column('temperature', sa.Float(), server_default="0.3"),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('tools_enabled', sa.JSON(), nullable=True),
        sa.Column('rag_enabled', sa.Boolean(), server_default="true"),
        sa.Column('identity_json', sa.JSON(), nullable=True),
        sa.Column('routing_rules', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 6. Agent Versions
    op.create_table(
        'agent_versions',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(64), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('tools_enabled', sa.JSON(), nullable=True),
        sa.Column('rag_enabled', sa.Boolean(), server_default="true"),
        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 7. Agent Policies
    op.create_table(
        'agent_policies',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(64), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('policy_type', sa.String(50), server_default="GUARDRAIL"),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('rules_json', sa.JSON(), nullable=True),
        sa.Column('enforcement_action', sa.String(50), server_default="BLOCK"),
        sa.Column('is_enabled', sa.Boolean(), server_default="true"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 8. Knowledge Sources
    op.create_table(
        'knowledge_sources',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(64), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), server_default="DOCUMENTS"),
        sa.Column('config_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 9. Knowledge Documents
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_id', sa.String(64), sa.ForeignKey('knowledge_sources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(64), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 10. Knowledge Chunks (with pgvector support)
    embedding_col = Vector(1536) if (is_postgres and HAS_PGVECTOR) else sa.JSON()
    op.create_table(
        'knowledge_chunks',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('doc_id', sa.String(64), sa.ForeignKey('knowledge_documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(64), nullable=True),
        sa.Column('chunk_index', sa.Integer(), server_default="0"),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('embedding', embedding_col, nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 11. Commerce Products
    op.create_table(
        'commerce_products',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), server_default="General"),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('compare_at_price', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(10), server_default="INR"),
        sa.Column('images', sa.JSON(), nullable=True),
        sa.Column('in_stock', sa.Boolean(), server_default="true"),
        sa.Column('total_inventory', sa.Integer(), server_default="0"),
        sa.Column('source_url', sa.String(500), nullable=True),
        sa.Column('searchable_text', sa.Text(), nullable=True),
        sa.Column('embedding', embedding_col, nullable=True),
        sa.Column('attributes_json', sa.JSON(), nullable=True),
        sa.Column('variants_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 12. Commerce Orders
    op.create_table(
        'commerce_orders',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_number', sa.String(64), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=False),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(10), server_default="INR"),
        sa.Column('status', sa.String(50), server_default="PAID"),
        sa.Column('carrier', sa.String(100), server_default="Bluedart Express"),
        sa.Column('tracking_number', sa.String(100), nullable=True),
        sa.Column('masked_address', sa.String(255), nullable=True),
        sa.Column('shipping_address_json', sa.JSON(), nullable=True),
        sa.Column('items_json', sa.JSON(), nullable=True),
        sa.Column('timeline_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 13. Commerce Carts
    op.create_table(
        'commerce_carts',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(128), unique=True, nullable=False),
        sa.Column('customer_identifier', sa.String(128), nullable=True),
        sa.Column('items_json', sa.JSON(), nullable=True),
        sa.Column('subtotal', sa.Float(), server_default="0.0"),
        sa.Column('discounts_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 14. Conversations
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(64), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_identifier', sa.String(128), nullable=True),
        sa.Column('channel', sa.String(50), server_default="PLAYGROUND"),
        sa.Column('title', sa.String(255), server_default="New Shopping Session"),
        sa.Column('status', sa.String(50), server_default="ACTIVE"),
        sa.Column('last_search_state', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 15. Messages
    op.create_table(
        'messages',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', sa.String(64), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('interactive_payload', sa.JSON(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 16. Execution Traces
    op.create_table(
        'execution_traces',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(64), nullable=False),
        sa.Column('conversation_id', sa.String(64), nullable=True),
        sa.Column('message_id', sa.String(64), nullable=True),
        sa.Column('intent', sa.String(100), server_default="GENERAL_QUERY"),
        sa.Column('goal', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Float(), server_default="0.0"),
        sa.Column('latency_ms', sa.Integer(), server_default="0"),
        sa.Column('tokens_used', sa.JSON(), nullable=True),
        sa.Column('planning_steps', sa.JSON(), nullable=True),
        sa.Column('tool_executions', sa.JSON(), nullable=True),
        sa.Column('retrieved_citations', sa.JSON(), nullable=True),
        sa.Column('policies_evaluated', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(50), server_default="SUCCESS"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 17. Deployments
    op.create_table(
        'deployments',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(64), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('public_key', sa.String(128), unique=True, nullable=False),
        sa.Column('allowed_domains', sa.JSON(), nullable=True),
        sa.Column('theme_config', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(50), server_default="ACTIVE"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 18. Api Keys
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(16), nullable=False),
        sa.Column('hashed_key', sa.String(128), unique=True, nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 19. Integrations
    op.create_table(
        'integrations',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), server_default="CONNECTED"),
        sa.Column('config_json', sa.JSON(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 20. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('workspace_id', sa.String(64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_id', sa.String(64), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(64), nullable=True),
        sa.Column('details_json', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Indices & Postgres RLS
    if is_postgres:
        for tbl in TENANT_TABLES:
            op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
            op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;")
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};")
            op.execute(f"""
                CREATE POLICY tenant_isolation_policy ON {tbl}
                USING (
                    workspace_id = current_setting('app.current_tenant_id', true)
                    OR current_setting('app.is_super_admin', true) = 'true'
                    OR current_setting('app.current_tenant_id', true) = ''
                );
            """)

        # HNSW Index for fast vector similarity search
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding_hnsw
            ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_commerce_products_embedding_hnsw
            ON commerce_products USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)

def downgrade() -> None:
    for tbl in reversed(TENANT_TABLES):
        op.drop_table(tbl)
    op.drop_table('users')
    op.drop_table('workspaces')
