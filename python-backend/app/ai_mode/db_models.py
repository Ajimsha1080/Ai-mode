import datetime
import os
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.database import Base

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

def get_vector_type(dim: int = 1536) -> Any:
    db_url = os.getenv("DATABASE_URL", "").lower()
    if HAS_PGVECTOR and "postgresql" in db_url:
        return Vector(dim)
    return JSON

def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)

# ==============================================================================
# AI MODE PERSISTENT MODELS (Additive, Isolated & Scoped to Tenant/Workspace)
# ==============================================================================

class AIModeConfigModel(Base):
    """Configuration & Feature Flags for AI Mode per Workspace."""
    __tablename__ = "ai_mode_configs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(default=True)
    brand_name: Mapped[str] = mapped_column(String(255), default="AI Mode Store")
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), default="sarvam-105b-conversations")
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    search_threshold: Mapped[float] = mapped_column(Float, default=0.45)
    rerank_enabled: Mapped[bool] = mapped_column(default=True)
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AIModeKnowledgeModel(Base):
    """Knowledge Sources for AI Mode (Website crawler, PDF, DOCX, TXT, CSV, FAQs)."""
    __tablename__ = "ai_mode_knowledge_sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="URL_CRAWLER")  # URL_CRAWLER, FILE_UPLOAD, FAQ, BUSINESS_INFO, PRODUCT_CATALOG
    status: Mapped[str] = mapped_column(String(50), default="READY")  # PENDING, SYNCING, READY, ERROR
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    documents: Mapped[list["AIModeKnowledgeDocModel"]] = relationship("AIModeKnowledgeDocModel", back_populates="source", cascade="all, delete-orphan")


class AIModeKnowledgeDocModel(Base):
    """Individual parsed documents under an AI Mode Knowledge Source."""
    __tablename__ = "ai_mode_knowledge_docs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(64), ForeignKey("ai_mode_knowledge_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(50), default="DOCUMENT")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source: Mapped["AIModeKnowledgeModel"] = relationship("AIModeKnowledgeModel", back_populates="documents")
    chunks: Mapped[list["AIModeKnowledgeChunkModel"]] = relationship("AIModeKnowledgeChunkModel", back_populates="document", cascade="all, delete-orphan")


class AIModeKnowledgeChunkModel(Base):
    """Vector & Lexical knowledge chunks for AI Mode hybrid retrieval."""
    __tablename__ = "ai_mode_knowledge_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_id: Mapped[str] = mapped_column(String(64), ForeignKey("ai_mode_knowledge_docs.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any] = mapped_column(get_vector_type(1536), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped["AIModeKnowledgeDocModel"] = relationship("AIModeKnowledgeDocModel", back_populates="chunks")


class AIModeConversationModel(Base):
    """Conversational Shopping Sessions for AI Mode."""
    __tablename__ = "ai_mode_conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    customer_identifier: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="AI Shopping Session")
    channel: Mapped[str] = mapped_column(String(50), default="PREVIEW")  # PREVIEW, WIDGET, API
    last_search_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    messages: Mapped[list["AIModeMessageModel"]] = relationship("AIModeMessageModel", back_populates="conversation", cascade="all, delete-orphan")


class AIModeMessageModel(Base):
    """Messages inside an AI Mode conversation."""
    __tablename__ = "ai_mode_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), ForeignKey("ai_mode_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(50), nullable=False)  # USER, ASSISTANT, SYSTEM
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(100), default="SHOPPING_QUERY")
    products_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    comparison_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped["AIModeConversationModel"] = relationship("AIModeConversationModel", back_populates="messages")


class AIModeDeploymentModel(Base):
    """AI Mode Independent Website Widget Deployments."""
    __tablename__ = "ai_mode_deployments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), default="Production AI Mode Widget")
    public_widget_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")  # ACTIVE, INACTIVE
    allowed_domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    theme_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    welcome_message: Mapped[str] = mapped_column(Text, default="Hi! 👋 Welcome to our AI-Powered Store. How can I help you find what you need today?")
    launcher_text: Mapped[str] = mapped_column(String(100), default="Ask AI Mode")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
