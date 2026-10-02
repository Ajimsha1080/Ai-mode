from typing import Any

from pydantic import BaseModel, Field

# ==============================================================================
# AI MODE PYDANTIC SCHEMAS
# ==============================================================================

class AIModeProduct(BaseModel):
    id: str
    title: str
    description: str | None = None
    price: float
    compare_at_price: float | None = None
    currency: str = "INR"
    category: str = "General"
    tags: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    in_stock: bool = True
    total_inventory: int = 0
    source_url: str | None = None
    score: float | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    variants: list[dict[str, Any]] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class AIModeSearchPlan(BaseModel):
    original_query: str
    clean_query: str
    intent: str  # DISCOVERY, RECOMMENDATION, COMPARISON, PRICE_FILTER, AVAILABILITY, FOLLOW_UP
    price_min: float | None = None
    price_max: float | None = None
    sort_by: str | None = None  # RELEVANCE, PRICE_LOW_TO_HIGH, PRICE_HIGH_TO_LOW, NEWEST
    attributes_filter: dict[str, Any] = Field(default_factory=dict)
    is_conversational_follow_up: bool = False
    comparison_targets: list[str] = Field(default_factory=list)


class AIModeSearchRequest(BaseModel):
    query: str
    workspace_id: str | None = None
    conversation_id: str | None = None
    page: int = 1
    page_size: int = 6
    filters: dict[str, Any] | None = None
    sort: str | None = None
    customer_context: dict[str, Any] | None = None


class AIModeSearchResponse(BaseModel):
    query: str
    search_plan: dict[str, Any]
    products: list[AIModeProduct]
    total_matches: int
    page: int
    page_size: int
    has_more: bool
    ai_summary: str
    suggestions: list[str] = Field(default_factory=list)
    retrieval_metrics: dict[str, Any] = Field(default_factory=dict)


class AIModeChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    session_id: str | None = None
    workspace_id: str | None = None
    customer_email: str | None = None
    channel: str = "PREVIEW"  # PREVIEW, WIDGET, API
    context: dict[str, Any] | None = None


class AIModeChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    response: str
    intent: str
    products: list[AIModeProduct] = Field(default_factory=list)
    comparison_matrix: dict[str, Any] | None = None
    suggestions: list[str] = Field(default_factory=list)
    pagination: dict[str, Any] | None = None
    search_plan: dict[str, Any] | None = None
    status: str = "SUCCESS"


class AIModeCompareRequest(BaseModel):
    product_ids: list[str]
    workspace_id: str | None = None
    user_query: str | None = None


class AIModeCompareResponse(BaseModel):
    products: list[AIModeProduct]
    comparison_table: list[dict[str, Any]]
    ai_summary: str
    best_for: dict[str, str] = Field(default_factory=dict)
    verdict: str


class AIModeRecommendationRequest(BaseModel):
    product_id: str | None = None
    user_intent: str | None = None
    workspace_id: str | None = None
    limit: int = 4
    context: dict[str, Any] | None = None


class AIModeRecommendationResponse(BaseModel):
    recommendations: list[AIModeProduct]
    reasoning: str
    strategy: str


class AIModeKnowledgeSourceCreate(BaseModel):
    name: str
    source_type: str  # URL_CRAWLER, FILE_UPLOAD, FAQ, BUSINESS_INFO, PRODUCT_CATALOG
    config: dict[str, Any] = Field(default_factory=dict)
    content: str | None = None


class AIModeConfigUpdate(BaseModel):
    is_enabled: bool | None = None
    brand_name: str | None = None
    system_prompt: str | None = None
    model_name: str | None = None
    temperature: float | None = None
    search_threshold: float | None = None
    rerank_enabled: bool | None = None
    settings: dict[str, Any] | None = None


class AIModeDeploymentCreate(BaseModel):
    name: str = "AI Mode Widget"
    allowed_domains: list[str] = Field(default_factory=list)
    theme_config: dict[str, Any] = Field(default_factory=dict)
    welcome_message: str = "Hi! 👋 Welcome to our AI Store. What can I find for you today?"
    launcher_text: str = "Ask AI Mode"


class AIModeDeploymentUpdate(BaseModel):
    name: str | None = None
    status: str | None = None  # ACTIVE, INACTIVE
    allowed_domains: list[str] | None = None
    theme_config: dict[str, Any] | None = None
    welcome_message: str | None = None
    launcher_text: str | None = None


class AIModeWidgetInitResponse(BaseModel):
    widget_id: str
    status: str
    workspace_id: str
    brand_name: str
    welcome_message: str
    launcher_text: str
    theme_config: dict[str, Any]
    initial_suggestions: list[str] = Field(default_factory=list)
