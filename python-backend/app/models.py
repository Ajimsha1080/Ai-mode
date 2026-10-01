from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User question or prompt")
    conversation_id: str | None = None
    workspace_id: str | None = None
    customer_identifier: str | None = "guest_user"
    channel: str | None = "PLAYGROUND"

class RAGQueryRequest(BaseModel):
    question: str = Field(..., description="Query for knowledge retrieval")
    workspace_id: str | None = None
    top_k: int | None = 3
    min_score: float | None = 0.20

class KnowledgeIngestRequest(BaseModel):
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Raw text content to chunk and index")
    workspace_id: str | None = None
    metadata: dict[str, Any] | None = None

class Citation(BaseModel):
    document_name: str
    chunk_text: str
    relevance_score: float
    is_verified: bool = True

class RAGPipelineTrace(BaseModel):
    query_understanding: dict[str, Any]
    query_rewrite: dict[str, Any]
    hybrid_retrieval: dict[str, Any]
    rrf_fusion: dict[str, Any]
    reranking: dict[str, Any]
    context_assembly: dict[str, Any]
    grounding_verification: dict[str, Any]

class ExecutionTrace(BaseModel):
    id: str
    conversation_id: str
    agent_id: str
    intent: str
    planning_steps: list[str]
    tool_executions: list[dict[str, Any]]
    retrieved_citations: list[Citation]
    rag_pipeline: RAGPipelineTrace | None = None
    latency_ms: int

class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    response: str
    interactive_payload: dict[str, Any] | None = None
    trace: ExecutionTrace
