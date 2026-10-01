import datetime
import os

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

def get_vector_type(dim: int = 1536):
    db_url = os.getenv("DATABASE_URL", "").lower()
    if HAS_PGVECTOR and "postgresql" in db_url:
        return Vector(dim)
    return JSON

def utcnow():
    return datetime.datetime.now(datetime.UTC)

# ==============================================================================
# 1. CORE TENANCY & IDENTITY
# ==============================================================================

class WorkspaceModel(Base):
    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    tier = Column(String(50), default="GROWTH") # FREE, STARTER, GROWTH, ENTERPRISE
    plan = Column(String(50), default="GROWTH")
    settings_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    members = relationship("WorkspaceMemberModel", back_populates="workspace", cascade="all, delete-orphan")
    agents = relationship("AgentModel", back_populates="workspace", cascade="all, delete-orphan")
    products = relationship("ProductModel", back_populates="workspace", cascade="all, delete-orphan")
    orders = relationship("OrderModel", back_populates="workspace", cascade="all, delete-orphan")
    knowledge_sources = relationship("KnowledgeSourceModel", back_populates="workspace", cascade="all, delete-orphan")
    deployments = relationship("DeploymentModel", back_populates="workspace", cascade="all, delete-orphan")
    api_keys = relationship("ApiKeyModel", back_populates="workspace", cascade="all, delete-orphan")
    tools = relationship("ToolModel", back_populates="workspace", cascade="all, delete-orphan")


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(50), default="MEMBER")
    is_super_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    memberships = relationship("WorkspaceMemberModel", back_populates="user", cascade="all, delete-orphan")


class WorkspaceMemberModel(Base):
    __tablename__ = "workspace_members"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="OWNER") # OWNER, ADMIN, EDITOR, VIEWER
    created_at = Column(DateTime(timezone=True), default=utcnow)

    workspace = relationship("WorkspaceModel", back_populates="members")
    user = relationship("UserModel", back_populates="memberships")


# ==============================================================================
# 2. AGENT CONFIGURATION & POLICIES
# ==============================================================================

class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace = relationship("WorkspaceModel", back_populates="agents")
    config = relationship("AgentConfigModel", uselist=False, back_populates="agent", cascade="all, delete-orphan")
    versions = relationship("AgentVersionModel", back_populates="agent", cascade="all, delete-orphan")
    policies = relationship("AgentPolicyModel", back_populates="agent", cascade="all, delete-orphan")
    conversations = relationship("ConversationModel", back_populates="agent", cascade="all, delete-orphan")


class AgentConfigModel(Base):
    __tablename__ = "agent_configs"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), ForeignKey("agents.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    model = Column(String(100), default="sarvam-105b-conversations")
    temperature = Column(Float, default=0.3)
    system_prompt = Column(Text, nullable=False)
    tools_enabled = Column(JSON, default=list)
    rag_enabled = Column(Boolean, default=True)
    identity_json = Column(JSON, default=dict)
    routing_rules = Column(JSON, default=dict)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    agent = relationship("AgentModel", back_populates="config")


class AgentVersionModel(Base):
    __tablename__ = "agent_versions"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    system_prompt = Column(Text, nullable=False)
    model = Column(String(100), nullable=False)
    tools_enabled = Column(JSON, default=list)
    rag_enabled = Column(Boolean, default=True)
    changelog = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    agent = relationship("AgentModel", back_populates="versions")


class AgentPolicyModel(Base):
    __tablename__ = "agent_policies"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_type = Column(String(50), default="GUARDRAIL")
    name = Column(String(100), nullable=False)
    rules_json = Column(JSON, default=dict)
    enforcement_action = Column(String(50), default="BLOCK")
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    agent = relationship("AgentModel", back_populates="policies")


class ToolModel(Base):
    __tablename__ = "tools"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    category = Column(String(100), default="COMMERCE")
    description = Column(Text, nullable=True)
    input_schema = Column(JSON, default=dict)
    output_schema = Column(JSON, default=dict)
    risk_level = Column(String(50), default="READ_ONLY")
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace = relationship("WorkspaceModel", back_populates="tools")


# ==============================================================================
# 3. KNOWLEDGE & RAG VECTOR STORAGE (PGVECTOR HNSW)
# ==============================================================================

class KnowledgeSourceModel(Base):
    __tablename__ = "knowledge_sources"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), default="DOCUMENTS")
    config_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace = relationship("WorkspaceModel", back_populates="knowledge_sources")

    documents = relationship("KnowledgeDocModel", back_populates="source", cascade="all, delete-orphan")


class KnowledgeDocModel(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(64), ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    source = relationship("KnowledgeSourceModel", back_populates="documents")
    chunks = relationship("KnowledgeChunkModel", back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunkModel(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_id = Column(String(64), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), nullable=True, index=True)
    chunk_index = Column(Integer, default=0)
    text = Column(Text, nullable=False)
    embedding = Column(get_vector_type(1536), nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    document = relationship("KnowledgeDocModel", back_populates="chunks")


# ==============================================================================
# 4. STRUCTURED COMMERCE ENGINE
# ==============================================================================

class ProductModel(Base):
    __tablename__ = "commerce_products"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="General", index=True)
    tags = Column(JSON, default=list)
    price = Column(Float, nullable=False, index=True)
    compare_at_price = Column(Float, nullable=True)
    currency = Column(String(10), default="INR")
    images = Column(JSON, default=list)
    in_stock = Column(Boolean, default=True, index=True)
    total_inventory = Column(Integer, default=0)
    source_url = Column(String(500), nullable=True)
    searchable_text = Column(Text, nullable=True)
    embedding = Column(get_vector_type(1536), nullable=True)
    attributes_json = Column(JSON, default=dict)
    variants_json = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace = relationship("WorkspaceModel", back_populates="products")


class OrderModel(Base):
    __tablename__ = "commerce_orders"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    order_number = Column(String(64), nullable=False, index=True)
    customer_email = Column(String(255), nullable=False, index=True)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(String(50), default="PAID", index=True)
    carrier = Column(String(100), default="Bluedart Express")
    tracking_number = Column(String(100), nullable=True)
    masked_address = Column(String(255), nullable=True)
    shipping_address_json = Column(JSON, default=dict)
    items_json = Column(JSON, default=list)
    timeline_json = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace = relationship("WorkspaceModel", back_populates="orders")


class CartModel(Base):
    __tablename__ = "commerce_carts"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(128), unique=True, index=True, nullable=False)
    customer_identifier = Column(String(128), nullable=True, index=True)
    items_json = Column(JSON, default=list)
    subtotal = Column(Float, default=0.0)
    discounts_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ==============================================================================
# 5. CONVERSATION SESSIONS, MESSAGES & TRACES
# ==============================================================================

class ConversationModel(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_identifier = Column(String(128), nullable=True, index=True)
    channel = Column(String(50), default="PLAYGROUND") # PLAYGROUND, WEBSITE, API, SHOPIFY
    title = Column(String(255), default="New Shopping Session")
    status = Column(String(50), default="ACTIVE")
    last_search_state = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    agent = relationship("AgentModel", back_populates="conversations")
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(50), nullable=False) # 'USER', 'AGENT', 'SYSTEM'
    content = Column(Text, nullable=False)
    interactive_payload = Column(JSON, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    conversation = relationship("ConversationModel", back_populates="messages")


class ExecutionTraceModel(Base):
    __tablename__ = "execution_traces"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), nullable=False, index=True)
    conversation_id = Column(String(64), nullable=True, index=True)
    message_id = Column(String(64), nullable=True, index=True)
    intent = Column(String(100), default="GENERAL_QUERY")
    goal = Column(Text, nullable=True)
    duration_ms = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    tokens_used = Column(JSON, default=dict)
    planning_steps = Column(JSON, default=list)
    tool_executions = Column(JSON, default=list)
    retrieved_citations = Column(JSON, default=list)
    policies_evaluated = Column(JSON, default=list)
    status = Column(String(50), default="SUCCESS")
    created_at = Column(DateTime(timezone=True), default=utcnow)


# ==============================================================================
# 6. PLATFORM DEPLOYMENTS, API KEYS, INTEGRATIONS & AUDIT LOGS
# ==============================================================================

class DeploymentModel(Base):
    __tablename__ = "deployments"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    public_key = Column(String(128), unique=True, index=True, nullable=False)
    allowed_domains = Column(JSON, default=list)
    theme_config = Column(JSON, default=dict)
    status = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace = relationship("WorkspaceModel", back_populates="deployments")


class ApiKeyModel(Base):
    __tablename__ = "api_keys"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key_prefix = Column(String(16), nullable=False, index=True)
    hashed_key = Column(String(128), unique=True, index=True, nullable=False)
    permissions = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    workspace = relationship("WorkspaceModel", back_populates="api_keys")


class IntegrationModel(Base):
    __tablename__ = "integrations"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(100), nullable=False) # SHOPIFY, STRIPE, RAZORPAY, SENDGRID
    status = Column(String(50), default="CONNECTED")
    config_json = Column(JSON, default=dict)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(64), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(64), nullable=True)
    details_json = Column(JSON, default=dict)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
