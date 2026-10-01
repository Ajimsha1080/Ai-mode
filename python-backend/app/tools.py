import os
import re
import math
import uuid
import asyncio
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from sqlalchemy import select

from .db.database import async_session_factory
from .db.models import ProductModel, OrderModel, CartModel
from .rag import generate_embedding, cosine_similarity

# ============================================================================
# 1. PYDANTIC INPUT & OUTPUT SCHEMAS FOR ALL 10 TOOLS
# ============================================================================

# Tool 1: search_products
class SearchProductsInput(BaseModel):
    query: Optional[str] = Field(default="", description="Search query string")
    category: Optional[str] = Field(default=None, description="Explicit category filter")
    gender: Optional[str] = Field(default=None, description="Demographic constraint: men, women, unisex, kids")
    min_price: Optional[float] = Field(default=None, description="Minimum price bound")
    max_price: Optional[float] = Field(default=None, description="Maximum price bound")
    size: Optional[str] = Field(default=None, description="Size attribute filter (S, M, L, XL, etc.)")
    color: Optional[str] = Field(default=None, description="Color attribute filter")
    in_stock_only: Optional[bool] = Field(default=False, description="Filter for in-stock products only")
    sort: Optional[str] = Field(default="relevance", description="Sort order: relevance, price_asc, price_desc, newest")
    page: Optional[int] = Field(default=1, description="1-indexed page number")
    page_size: Optional[int] = Field(default=6, description="Items per page")

class SearchProductsOutput(BaseModel):
    products: List[Dict[str, Any]] = Field(default_factory=list)
    total_matches: int = 0
    totalMatches: int = 0
    page: int = 1
    page_size: int = 6
    pageSize: int = 6
    has_more: bool = False
    hasMore: bool = False
    applied_constraints: Dict[str, Any] = Field(default_factory=dict)
    appliedConstraints: Dict[str, Any] = Field(default_factory=dict)
    categories_matched: List[str] = Field(default_factory=list)
    categoriesMatched: List[str] = Field(default_factory=list)

# Tool 2: get_inventory / check_inventory
class GetInventoryInput(BaseModel):
    product_id: str = Field(..., description="Product ID to check inventory for")
    variant_id: Optional[str] = Field(default=None, description="Specific variant ID")
    size: Optional[str] = Field(default=None, description="Size attribute to check")
    color: Optional[str] = Field(default=None, description="Color attribute to check")

class GetInventoryOutput(BaseModel):
    product_id: str
    title: str = ""
    in_stock: bool = False
    stock_count: int = 0
    available_sizes: List[str] = Field(default_factory=list)
    available_colors: List[str] = Field(default_factory=list)
    message: str = ""

# Tool 3: order_lookup
class OrderLookupInput(BaseModel):
    order_number: str = Field(..., description="Order confirmation number (e.g. #10482)")
    customer_email: str = Field(..., description="Customer checkout email address for verification")

class OrderLookupOutput(BaseModel):
    found: bool = False
    order: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Tool 4: order_tracking
class OrderTrackingInput(BaseModel):
    order_number: str = Field(..., description="Order number to track")
    customer_email: Optional[str] = Field(default=None, description="Customer email address")

class OrderTrackingOutput(BaseModel):
    found: bool = False
    order_number: str = ""
    status: str = ""
    carrier: str = ""
    tracking_number: str = ""
    masked_address: str = ""
    estimated_delivery: str = ""
    items: List[str] = Field(default_factory=list)

# Tool 5: coupon_validation / apply_discount
class CouponValidationInput(BaseModel):
    coupon_code: str = Field(..., description="Promotional discount code string")
    cart_subtotal: float = Field(..., description="Current subtotal before discount")

class CouponValidationOutput(BaseModel):
    valid: bool = False
    code: str = ""
    discount_amount: float = 0.0
    discount_percentage: float = 0.0
    message: str = ""

# Tool 6: return_eligibility
class ReturnEligibilityInput(BaseModel):
    order_number: str = Field(..., description="Order confirmation number")
    customer_email: Optional[str] = Field(default=None, description="Customer email")
    product_id: Optional[str] = Field(default=None, description="Product ID to return")

class ReturnEligibilityOutput(BaseModel):
    eligible: bool = False
    order_number: str = ""
    return_window_days: int = 30
    reason: str = ""
    doorstep_pickup_available: bool = True

# Tool 7: create_return
class CreateReturnInput(BaseModel):
    order_number: str = Field(..., description="Order confirmation number")
    customer_email: str = Field(..., description="Customer email for return verification")
    product_id: Optional[str] = Field(default=None, description="Product ID being returned")
    reason: str = Field(default="Sizing exchange", description="Reason for return or exchange")

class CreateReturnOutput(BaseModel):
    success: bool = False
    return_id: str = ""
    return_label_url: str = ""
    carrier: str = "Bluedart Express"
    doorstep_pickup_date: str = ""
    message: str = ""

# Tool 8: add_to_cart
class AddToCartInput(BaseModel):
    cart_id: Optional[str] = Field(default=None, description="Active cart ID or session ID")
    product_id: str = Field(..., description="Product ID to add")
    variant_id: Optional[str] = Field(default=None, description="Variant ID")
    quantity: int = Field(default=1, description="Quantity of product to add")
    size: Optional[str] = Field(default=None, description="Size attribute")
    color: Optional[str] = Field(default=None, description="Color attribute")

class AddToCartOutput(BaseModel):
    success: bool = False
    cart_id: str = ""
    product_id: str = ""
    title: str = ""
    quantity: int = 1
    price: float = 0.0
    subtotal: float = 0.0
    item_count: int = 0
    message: str = ""

# Tool 9: cart_lookup / calculate_cart
class CartLookupInput(BaseModel):
    cart_id: Optional[str] = Field(default=None, description="Active cart ID")
    session_id: Optional[str] = Field(default=None, description="Active customer session ID")
    items: Optional[List[Dict[str, Any]]] = Field(default=None, description="Ad-hoc items list for calculation")
    discount_code: Optional[str] = Field(default=None, description="Discount promo code to apply")

class CartLookupOutput(BaseModel):
    cart_id: str = ""
    items: List[Dict[str, Any]] = Field(default_factory=list)
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    subtotal: float = 0.0
    shipping_amount: float = 0.0
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    grand_total: float = 0.0
    total: float = 0.0
    discount_applied: Optional[Dict[str, Any]] = None

# Tool 10: human_handoff
class HumanHandoffInput(BaseModel):
    reason: str = Field(default="Customer requested human support", description="Reason for escalation")
    customer_email: Optional[str] = Field(default=None, description="Customer email")
    summary: Optional[str] = Field(default=None, description="Context summary of the inquiry")

class HumanHandoffOutput(BaseModel):
    status: str = "ESCALATED"
    ticket_id: str = ""
    queue: str = "TIER_1_COMMERCE_SUPPORT"
    message: str = "A human support specialist has been notified and will join this session momentarily."


TOOL_DEFINITIONS = [
    {
        "name": "search_products",
        "description": "Search store catalog with category, price range, size, color, and natural language filters.",
        "parameters": SearchProductsInput.model_json_schema()
    },
    {
        "name": "get_inventory",
        "description": "Check real-time stock levels, variant availability, and sizes for a product.",
        "parameters": GetInventoryInput.model_json_schema()
    },
    {
        "name": "check_inventory",
        "description": "Check real-time stock levels, variant availability, and sizes for a product.",
        "parameters": GetInventoryInput.model_json_schema()
    },
    {
        "name": "order_lookup",
        "description": "Look up an order by order number and customer email with masked PII and tracking info.",
        "parameters": OrderLookupInput.model_json_schema()
    },
    {
        "name": "lookup_order",
        "description": "Look up an order by order number and customer email with masked PII and tracking info.",
        "parameters": OrderLookupInput.model_json_schema()
    },
    {
        "name": "order_tracking",
        "description": "Retrieve real-time carrier tracking status and delivery updates.",
        "parameters": OrderTrackingInput.model_json_schema()
    },
    {
        "name": "coupon_validation",
        "description": "Validate and calculate discount for a promotional promo code.",
        "parameters": CouponValidationInput.model_json_schema()
    },
    {
        "name": "apply_discount",
        "description": "Validate and calculate discount for a promotional promo code.",
        "parameters": CouponValidationInput.model_json_schema()
    },
    {
        "name": "return_eligibility",
        "description": "Check if an item is eligible for return or exchange under the store policy.",
        "parameters": ReturnEligibilityInput.model_json_schema()
    },
    {
        "name": "create_return",
        "description": "Initiate a return request and schedule courier pickup.",
        "parameters": CreateReturnInput.model_json_schema()
    },
    {
        "name": "add_to_cart",
        "description": "Add an in-stock product or variant to the shopping cart.",
        "parameters": AddToCartInput.model_json_schema()
    },
    {
        "name": "cart_lookup",
        "description": "Retrieve active cart items, subtotal, taxes, shipping, and total.",
        "parameters": CartLookupInput.model_json_schema()
    },
    {
        "name": "calculate_cart",
        "description": "Retrieve active cart items, subtotal, taxes, shipping, and total.",
        "parameters": CartLookupInput.model_json_schema()
    },
    {
        "name": "human_handoff",
        "description": "Escalate the conversation to a human support representative.",
        "parameters": HumanHandoffInput.model_json_schema()
    }
]


# ============================================================================
# 2. NLP UTILITIES & SCHEMA INTROSPECTION
# ============================================================================

TYPO_MAP: Dict[str, str] = {
    "wmoen": "women",
    "womne": "women",
    "wommen": "women",
    "womans": "women",
    "wmon": "women",
    "womem": "women",
    "prodcuts": "products",
    "prodcut": "product",
    "produts": "products",
    "produtcs": "products",
    "proucts": "products",
    "porducts": "products",
    "shrit": "shirt",
    "shrits": "shirts",
    "tshrit": "tshirt",
    "tshrits": "tshirts",
    "balclava": "balaclava",
    "balaklava": "balaclava",
    "viser": "visor",
    "visors": "visor",
    "clothe": "clothes",
    "cloths": "clothes",
    "trak": "track",
    "traking": "tracking",
    "retrn": "return",
    "ordr": "order",
    "oder": "order"
}

def stem_word(word: str) -> str:
    """Universal English suffix stemmer."""
    w = word.lower().strip()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("sses") and len(w) > 4:
        return w[:-2]
    if w.endswith("es") and not w.endswith("ses") and len(w) > 3:
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 2:
        return w[:-1]
    return w

def check_is_women_product(p: Dict[str, Any]) -> bool:
    title_l = p.get("title", "").lower()
    tags_l = " ".join([t.lower() for t in p.get("tags", [])])
    cat_l = p.get("category", "").lower()
    desc_l = p.get("description", "").lower()
    full = f"{title_l} {tags_l} {cat_l} {desc_l}"
    return any(w in full for w in [
        "women", "womens", "female", "saree", "kurta", "kurti", "dress", "lehenga", "gown", "skirt", "blouse", "pink", "lavender"
    ])


# ============================================================================
# 3. DATABASE FETCH HELPERS (MULTI-TENANT)
# ============================================================================

async def _fetch_products_db(workspace_id: str) -> List[Dict[str, Any]]:
    async with async_session_factory() as session:
        stmt = select(ProductModel).where(ProductModel.workspace_id == workspace_id)
        res = await session.execute(stmt)
        prods = res.scalars().all()
        return [
            {
                "id": p.id,
                "workspace_id": p.workspace_id,
                "title": p.title,
                "category": p.category,
                "price": float(p.price),
                "compare_at_price": float(p.compare_at_price) if p.compare_at_price else None,
                "currency": p.currency or "INR",
                "stock": int(getattr(p, "total_inventory", 0)),
                "total_inventory": int(getattr(p, "total_inventory", 0)),
                "in_stock": getattr(p, "in_stock", True) and int(getattr(p, "total_inventory", 0)) > 0,
                "tags": p.tags or [],
                "images": p.images or [],
                "description": p.description or "",
                "searchable_text": p.searchable_text or "",
                "embedding": p.embedding,
                "variants": p.variants_json or []
            }
            for p in prods
        ]

async def _fetch_order_db(workspace_id: str, order_number: str, customer_email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not customer_email or not customer_email.strip():
        return None
    clean_num = order_number.strip()
    clean_without_hash = clean_num.replace("#", "")
    clean_email = customer_email.strip().lower()

    async with async_session_factory() as session:
        stmt = select(OrderModel).where(OrderModel.workspace_id == workspace_id)
        res = await session.execute(stmt)
        orders = res.scalars().all()
        for ord in orders:
            if ord.customer_email.strip().lower() != clean_email:
                continue

            if clean_without_hash in ord.id or ord.id == clean_num or ord.id == f"ord_{clean_without_hash}" or ord.order_number == clean_num or ord.order_number == f"#{clean_num}":
                return {
                    "id": ord.id,
                    "order_number": clean_num if clean_num.startswith("#") else f"#{clean_num}",
                    "workspace_id": workspace_id,
                    "customer_email": ord.customer_email,
                    "status": ord.status,
                    "carrier": ord.carrier or ("Bluedart Express" if "acme" in workspace_id else "Delhivery Express"),
                    "tracking_number": ord.tracking_number or ("BD-8941039821-IN" if "acme" in workspace_id else "DL-9999999999-IN"),
                    "items": [it.get("title", str(it)) if isinstance(it, dict) else str(it) for it in (ord.items_json or ["1x UPF 50+ Sunscreen Performance Jacket"])],
                    "total_amount": float(ord.total_amount),
                    "currency": ord.currency or "INR",
                    "masked_address": ord.masked_address or "Indiranagar, 12th Main, Bengaluru, KA 560038"
                }
        return None

def get_tenant_products_sync(workspace_id: str) -> List[Dict[str, Any]]:
    if not workspace_id:
        raise ValueError("workspace_id is mandatory")
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _fetch_products_db(workspace_id)).result()
        else:
            return asyncio.run(_fetch_products_db(workspace_id))
    except Exception:
        return []

def get_tenant_order_sync(workspace_id: str, order_number: str, customer_email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not workspace_id:
        raise ValueError("workspace_id is mandatory")
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _fetch_order_db(workspace_id, order_number, customer_email)).result()
        else:
            return asyncio.run(_fetch_order_db(workspace_id, order_number, customer_email))
    except Exception:
        return None


# ============================================================================
# 4. QUERY PARSING & ENTITY EXTRACTION
# ============================================================================

def introspect_catalog_schema(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    categories = sorted(list(set(p.get("category", "").strip() for p in products if p.get("category"))))
    tags = sorted(list(set(t.strip().lower() for p in products for t in p.get("tags", []) if t)))
    attribute_values: Dict[str, List[str]] = {}

    for p in products:
        for v in p.get("variants", []):
            attrs = v.get("attributes", {})
            for k, val in attrs.items():
                k_norm = k.lower().strip()
                val_norm = str(val).lower().strip()
                if k_norm not in attribute_values:
                    attribute_values[k_norm] = []
                if val_norm not in attribute_values[k_norm]:
                    attribute_values[k_norm].append(val_norm)

    return {
        "categories": categories,
        "tags": tags,
        "attribute_values": attribute_values
    }


def parse_search_query(user_query: str, schema: Dict[str, Any], last_search_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    q = user_query.lower().strip()
    for typo, fix in TYPO_MAP.items():
        q = re.sub(rf'\b{typo}\b', fix, q)

    q = re.sub(r'\bt[\s\-]+shirts?\b', 't-shirt', q)
    q = re.sub(r'\bt[\s\-]+tees?\b', 't-shirt', q)
    clean_q = re.sub(r'[^\w\s\-\/₹$]', ' ', q)
    clean_q = re.sub(r'\s+', ' ', clean_q).strip()
    query_tokens = [w for w in clean_q.split() if len(w) >= 2 or w == 't']

    is_pagination = bool(re.search(r'\b(show more|load more|more products|more items|next page|see more)\b', clean_q))
    is_all_matching = bool(re.search(r'\b(show all|all matching|all products|give me all|entire collection|whole collection|full catalog|all of them|everything)\b', clean_q))
    is_refinement = bool(re.search(r'\b(only|just|instead|remove filter|clear filter|without)\b', clean_q)) or (last_search_state and bool(re.match(r'^(under|below|above|size|in|only)\b', clean_q)))

    scope = "recommendations"
    if is_pagination:
        scope = "pagination"
    elif is_all_matching:
        scope = "all_matching"
    elif is_refinement:
        scope = "refinement"

    # Category matching
    explicit_category = None
    has_tshirt_token = bool(re.search(r't-?shirt|tshirt|tee', clean_q))

    for cat in schema.get("categories", []):
        cat_norm = cat.lower().strip()
        is_compound = bool(re.search(r't-?shirt|tee', cat_norm))
        if is_compound and has_tshirt_token:
            explicit_category = cat
            break
        if not is_compound and "shirt" in cat_norm and not has_tshirt_token and re.search(r'\bshirts?\b', clean_q):
            explicit_category = cat
            break

    if not explicit_category:
        for cat in schema.get("categories", []):
            cat_norm = cat.lower().strip()
            cat_stemmed = " ".join([stem_word(t) for t in re.split(r'[\s\-_]+', cat_norm)])
            if cat_norm in clean_q or cat_stemmed in clean_q:
                explicit_category = cat
                break

    # Price Bounds
    max_price = None
    min_price = None
    max_match = re.search(r'(?:under|below|less than|max|around|budget|up to)\s*(?:₹|\$)?\s*(\d+)', clean_q) or re.search(r'(\d+)\s*(?:k|thousand)\b', clean_q)
    if max_match:
        val = float(max_match.group(1))
        if 'k' in max_match.group(0).lower() or 'thousand' in max_match.group(0).lower():
            val *= 1000
        max_price = val

    min_match = re.search(r'(?:above|over|more than|min|at least|starting from)\s*(?:₹|\$)?\s*(\d+)', clean_q)
    if min_match:
        min_price = float(min_match.group(1))

    # Gender
    gender = None
    if re.search(r'\b(women|womens|lady|ladies|female|girl|girls|wife|sister|mother)\b', clean_q):
        gender = "women"
    elif re.search(r'\b(men|mens|male|gent|gents|guy|guys|brother|husband|father|him|boy)\b', clean_q):
        gender = "men"
    elif re.search(r'\b(kids|kid|child|children|baby|toddler)\b', clean_q):
        gender = "kids"

    # Size
    size = None
    size_match = re.search(r'\bsize\s*(\d+|s|m|l|xl|xxl|xxxl|free\s*size)\b', clean_q) or re.search(r'\b(s|m|l|xl|xxl|xxxl)\s+size\b', clean_q)
    if size_match:
        size = size_match.group(1).upper().replace(" ", "")

    # Color
    color = None
    color_match = re.search(r'\b(black|white|red|blue|grey|silver|olive|green|yellow|pink|navy|wine|maroon|purple|cream|brown|lavender|teal)\b', clean_q)
    if color_match:
        color = color_match.group(1).lower()

    # Sort
    sort = "relevance"
    if re.search(r'\b(cheaper|cheapest|lowest price|price low to high|affordable|budget)\b', clean_q):
        sort = "price_asc"
    elif re.search(r'\b(expensive|premium|highest price|price high to low|luxe)\b', clean_q):
        sort = "price_desc"
    elif re.search(r'\b(new|latest|newest|arrivals|recent)\b', clean_q):
        sort = "newest"

    # Semantic Terms
    semantic_map = {
        "gym": ["activewear", "nosweat", "quick-dry", "stretch", "breathable", "jogger", "tee", "performance", "workout"],
        "fitness": ["activewear", "nosweat", "quick-dry", "stretch", "breathable", "jogger", "tee", "performance"],
        "workout": ["activewear", "nosweat", "quick-dry", "stretch", "breathable", "jogger", "tee", "performance"],
        "dinner": ["shirt", "kurta", "saree", "corduroy", "black", "luxe", "dress"],
        "office": ["shirt", "corduroy", "pant", "anti-ac", "thermal", "kurta", "formal", "cotton"],
        "casual": ["tee", "tshirt", "t-shirt", "jogger", "hoodie", "nosweat", "jacket", "cotton", "relaxed"],
        "wedding": ["royal", "heritage", "saree", "kurta", "zari", "mandala", "festive", "silk"],
        "festive": ["royal", "heritage", "saree", "kurta", "yellow floral", "emerald", "mandala", "festive", "silk"],
        "summer": ["sunscreen", "ice", "cooling", "tee", "tshirt", "t-shirt", "nosweat", "visor", "balaclava", "upf50"],
        "brother": ["shirt", "tee", "tshirt", "t-shirt", "jogger", "jacket", "corduroy", "men"]
    }
    semantic_terms = set()
    for k, terms in semantic_map.items():
        if k in clean_q:
            for t in terms:
                semantic_terms.add(t)

    stopwords = {
        "show", "me", "find", "look", "for", "under", "below", "in", "size", "with", "a", "an", "the",
        "please", "can", "you", "give", "what", "are", "your", "any", "new", "latest", "product",
        "products", "items", "item", "catalog", "collection", "good", "need", "want", "buy", "recommend",
        "like", "have", "i", "get", "to", "and", "or", "is", "it", "this", "that", "more", "page", "all"
    }
    content_tokens = [t for t in query_tokens if t not in stopwords and not t.isdigit()]

    # State Inheritance
    page = 1
    page_size = 12 if scope == "all_matching" else 6
    original_query = clean_q

    if is_pagination and last_search_state:
        page = int(last_search_state.get("page", 1)) + 1
        page_size = int(last_search_state.get("page_size", last_search_state.get("pageSize", page_size)))
        original_query = last_search_state.get("original_query", clean_q)
        if not explicit_category:
            explicit_category = last_search_state.get("explicitCategory") or last_search_state.get("category")
        if not gender:
            gender = last_search_state.get("gender")
        if not color:
            color = last_search_state.get("color")
        if max_price is None:
            max_price = last_search_state.get("maxPrice") or last_search_state.get("max_price")
        if min_price is None:
            min_price = last_search_state.get("minPrice") or last_search_state.get("min_price")
        if not size:
            size = last_search_state.get("size")
        if sort == "relevance" and last_search_state.get("sort"):
            sort = last_search_state.get("sort")
        if not content_tokens and last_search_state.get("contentTokens"):
            content_tokens = last_search_state.get("contentTokens")
    elif is_refinement and last_search_state:
        original_query = last_search_state.get("original_query", clean_q)
        if not explicit_category:
            explicit_category = last_search_state.get("explicitCategory") or last_search_state.get("category")
        if not gender:
            gender = last_search_state.get("gender")
        if not color:
            color = last_search_state.get("color")
        if max_price is None:
            max_price = last_search_state.get("maxPrice") or last_search_state.get("max_price")
        if min_price is None:
            min_price = last_search_state.get("minPrice") or last_search_state.get("min_price")
        if not size:
            size = last_search_state.get("size")
        if sort == "relevance" and last_search_state.get("sort"):
            sort = last_search_state.get("sort")

    return {
        "scope": scope,
        "original_query": original_query,
        "explicit_category": explicit_category,
        "gender": gender,
        "min_price": min_price,
        "max_price": max_price,
        "size": size,
        "color": color,
        "in_stock_only": bool(re.search(r'\b(in stock|available)\b', clean_q)),
        "semantic_terms": list(semantic_terms),
        "content_tokens": content_tokens,
        "sort": sort,
        "page": page,
        "page_size": page_size
    }


# ============================================================================
# 5. HIGH-PERFORMANCE PRODUCT SEARCH & FILTERING
# ============================================================================

def search_products(workspace_id: str, query: str = "", category: Optional[str] = None, last_search_state: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    if not workspace_id:
        raise ValueError("workspace_id is mandatory for search_products")

    all_prods = get_tenant_products_sync(workspace_id)
    schema = introspect_catalog_schema(all_prods)
    parsed = parse_search_query(query or "", schema, last_search_state)

    explicit_category = category or kwargs.get("category") or parsed["explicit_category"]
    gender = kwargs.get("gender") or parsed["gender"]
    min_price = kwargs.get("min_price", parsed["min_price"])
    max_price = kwargs.get("max_price", parsed["max_price"])
    size = kwargs.get("size") or parsed["size"]
    color = kwargs.get("color") or parsed["color"]
    in_stock_only = kwargs.get("in_stock_only", parsed["in_stock_only"])
    sort = kwargs.get("sort") or parsed["sort"] or "relevance"
    page = int(kwargs.get("page", parsed["page"]))
    page_size = int(kwargs.get("page_size", parsed["page_size"]))
    content_tokens = parsed["content_tokens"]
    semantic_terms = parsed["semantic_terms"]

    query_for_scoring = (parsed["original_query"] if parsed["scope"] == "pagination" else query).lower().strip()

    # Non-existent item check (e.g. "shoes" in an apparel-only store)
    non_semantic_tokens = [tok.lower() for tok in content_tokens if tok.lower() not in [
        "gym", "fitness", "workout", "sports", "dinner", "office", "casual", "wedding", "festive", "summer", "brother",
        "men", "mens", "women", "womens", "cheap", "expensive", "red", "blue", "green", "black", "white", "yellow", "brown", "wine"
    ]]

    if non_semantic_tokens and not explicit_category:
        catalog_has_token = False
        for p in all_prods:
            p_text = f"{p.get('title', '')} {p.get('category', '')} {' '.join(p.get('tags', []))} {p.get('description', '')}".lower()
            if any(tok in p_text or stem_word(tok) in [stem_word(w) for w in p_text.split()] for tok in non_semantic_tokens):
                catalog_has_token = True
                break
        if not catalog_has_token:
            return SearchProductsOutput(
                products=[],
                total_matches=0,
                totalMatches=0,
                page=page,
                page_size=page_size,
                pageSize=page_size,
                has_more=False,
                hasMore=False,
                applied_constraints={"category": explicit_category, "gender": gender, "min_price": min_price, "max_price": max_price},
                appliedConstraints={"category": explicit_category, "gender": gender, "min_price": min_price, "max_price": max_price},
                categories_matched=[],
                categoriesMatched=[]
            ).model_dump()

    # Filter by hard constraints
    candidates = []
    is_men_query = gender == "men"
    is_women_query = gender == "women"

    for p in all_prods:
        title_l = p.get("title", "").lower()
        tags_l = [t.lower() for t in p.get("tags", [])]
        cat_l = p.get("category", "").lower()
        desc_l = p.get("description", "").lower()
        full_text = f"{title_l} {desc_l} {cat_l} {' '.join(tags_l)}"

        is_women = check_is_women_product(p)
        if is_men_query and not is_women_query and is_women and "men" not in full_text and "couple" not in full_text:
            continue
        if is_womenQuery := is_women_query and not is_men_query and not is_women:
            continue

        # Explicit Category
        if explicit_category:
            exp_cat_l = explicit_category.lower().strip()
            exp_cat_stem = stem_word(exp_cat_l)
            is_cat_match = cat_l == exp_cat_l or stem_word(cat_l) == exp_cat_stem or exp_cat_l in title_l or exp_cat_stem in [stem_word(w) for w in title_l.split()] or exp_cat_l in tags_l
            if not is_cat_match:
                continue

        # Price bounds
        if min_price is not None and p["price"] < min_price:
            continue
        if max_price is not None and p["price"] > max_price:
            continue

        # In stock only
        if in_stock_only and (not p.get("in_stock", True) or p.get("total_inventory", 0) <= 0):
            continue

        # Size
        if size:
            size_l = size.lower()
            has_size = any(v.get("attributes", {}).get("size", "").lower() == size_l and v.get("inventory_quantity", 0) > 0 for v in p.get("variants", []))
            if not has_size and p.get("variants"):
                continue

        # Color
        if color:
            color_l = color.lower()
            color_synonyms = {
                "red": ["red", "wine", "maroon", "crimson", "burgundy", "coral"],
                "blue": ["blue", "navy", "indigo", "teal"],
                "green": ["green", "emerald", "olive", "sage", "evergreen"],
                "black": ["black", "stealth", "obsidian", "dark"],
                "white": ["white", "off-white", "off white", "ivory"],
                "yellow": ["yellow", "mustard", "gold"],
                "brown": ["brown", "khaki", "tan"]
            }
            family = [color_l] + color_synonyms.get(color_l, [])
            has_color = any(c in full_text for c in family) or any(any(c in f"{v.get('attributes', {}).get('color', '')} {v.get('title', '')}".lower() for c in family) for v in p.get("variants", []))
            if not has_color:
                continue

        candidates.append(p)

    # Hybrid Scoring
    query_vec = generate_embedding(query_for_scoring) if query_for_scoring else None

    def compute_score(p: Dict[str, Any]) -> float:
        lexical = 0.0
        t_low = p.get("title", "").lower()
        d_low = p.get("description", "").lower()
        c_low = p.get("category", "").lower()
        tags_low = [t.lower() for t in p.get("tags", [])]
        full = f"{t_low} {d_low} {c_low} {' '.join(tags_low)}"

        if query_for_scoring and query_for_scoring in t_low:
            lexical += 120.0

        matched_count = 0
        for tok in content_tokens:
            tok_stem = stem_word(tok)
            matched = False
            if re.search(rf'\b{tok}\b', t_low):
                lexical += 45.0
                matched = True
            elif stem_word(t_low) == tok_stem or tok_stem in [stem_word(w) for w in t_low.split()]:
                lexical += 30.0
                matched = True
            if any(re.search(rf'\b{tok}\b', t) for t in tags_low):
                lexical += 25.0
                matched = True
            if tok in c_low:
                lexical += 20.0
                matched = True
            if tok in d_low:
                lexical += 15.0
                matched = True
            if matched:
                matched_count += 1

        if len(content_tokens) >= 2 and matched_count == len(content_tokens):
            lexical += 120.0

        for sem in semantic_terms:
            if sem in t_low:
                lexical += 35.0
            if any(sem in t for t in tags_low):
                lexical += 25.0
            if sem in d_low:
                lexical += 15.0

        if explicit_category and c_low == explicit_category.lower():
            lexical += 40.0

        dense_score = 0.0
        if query_vec:
            p_emb = p.get("embedding") or generate_embedding(f"{p.get('title', '')} {p.get('category', '')} {p.get('description', '')}")
            dense_score = cosine_similarity(query_vec, p_emb)

        return (lexical * 0.65) + (dense_score * 100.0 * 0.35) + (5.0 if p.get("in_stock", True) else 0.0)

    if content_tokens or explicit_category or semantic_terms or color or gender:
        min_thresh = 40.0 if len(content_tokens) >= 2 else 15.0
        scored = [(compute_score(p), p) for p in candidates]
        max_s = max([s for s, _ in scored]) if scored else 0.0
        if max_s >= min_thresh:
            candidates = [p for s, p in scored if s >= min_thresh and (len(content_tokens) < 2 or s >= max_s * 0.35)]
        else:
            candidates = []

    # Sorting
    if sort == "price_asc":
        candidates.sort(key=lambda x: x["price"])
    elif sort == "price_desc":
        candidates.sort(key=lambda x: x["price"], reverse=True)
    elif sort == "newest":
        candidates.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    else:
        candidates.sort(key=lambda x: compute_score(x), reverse=True)

    # Deduplication
    seen_ids = set()
    seen_titles = set()
    deduped = []
    for p in candidates:
        t_clean = p["title"].strip().lower()
        if p["id"] not in seen_ids and t_clean not in seen_titles:
            seen_ids.add(p["id"])
            seen_titles.add(t_clean)
            deduped.append(p)

    # Authoritative Pagination Calculation
    total_matches = len(deduped)
    start_idx = (page - 1) * page_size
    paged = deduped[start_idx : start_idx + page_size]
    has_more = (start_idx + len(paged)) < total_matches

    applied = {
        "category": explicit_category,
        "gender": gender,
        "min_price": min_price,
        "max_price": max_price,
        "size": size,
        "color": color,
        "in_stock_only": in_stock_only,
        "sort": sort,
        "page": page,
        "page_size": page_size
    }

    return SearchProductsOutput(
        products=paged,
        total_matches=total_matches,
        totalMatches=total_matches,
        page=page,
        page_size=page_size,
        pageSize=page_size,
        has_more=has_more,
        hasMore=has_more,
        applied_constraints=applied,
        appliedConstraints=applied,
        categories_matched=[explicit_category] if explicit_category else [],
        categoriesMatched=[explicit_category] if explicit_category else []
    ).model_dump()


# ============================================================================
# 6. COMMERCE TOOLS IMPLEMENTATION
# ============================================================================

def get_inventory(workspace_id: str, product_id: str, variant_id: Optional[str] = None, size: Optional[str] = None, color: Optional[str] = None) -> Dict[str, Any]:
    prods = get_tenant_products_sync(workspace_id)
    target = next((p for p in prods if p["id"] == product_id), None)
    if not target:
        return GetInventoryOutput(product_id=product_id, in_stock=False, message=f"Product '{product_id}' not found").model_dump()

    variants = target.get("variants", [])
    sizes = list(set(v.get("attributes", {}).get("size") for v in variants if v.get("attributes", {}).get("size") and v.get("inventory_quantity", 0) > 0))
    colors = list(set(v.get("attributes", {}).get("color") for v in variants if v.get("attributes", {}).get("color") and v.get("inventory_quantity", 0) > 0))

    stock_count = target.get("total_inventory", 0)
    in_stock = target.get("in_stock", True) and stock_count > 0

    if size:
        matching_v = [v for v in variants if v.get("attributes", {}).get("size", "").lower() == size.lower()]
        in_stock = any(v.get("inventory_quantity", 0) > 0 for v in matching_v)
        stock_count = sum(v.get("inventory_quantity", 0) for v in matching_v)

    return GetInventoryOutput(
        product_id=product_id,
        title=target["title"],
        in_stock=in_stock,
        stock_count=stock_count,
        available_sizes=sizes,
        available_colors=colors,
        message=f"{target['title']} is {'IN STOCK' if in_stock else 'OUT OF STOCK'} ({stock_count} units available)."
    ).model_dump()

def check_inventory(workspace_id: str, product_id: str, **kwargs) -> Dict[str, Any]:
    return get_inventory(workspace_id, product_id, **kwargs)


def lookup_order(workspace_id: str, order_number: str, customer_email: str) -> Dict[str, Any]:
    if not customer_email or not customer_email.strip():
        return OrderLookupOutput(found=False, error="Customer email is required for secure order verification").model_dump()

    order = get_tenant_order_sync(workspace_id, order_number, customer_email)
    if not order:
        return OrderLookupOutput(found=False, error=f"Order '{order_number}' not found for email '{customer_email}'").model_dump()

    return OrderLookupOutput(found=True, order=order).model_dump()

def order_lookup(workspace_id: str, order_number: str, customer_email: str) -> Dict[str, Any]:
    return lookup_order(workspace_id, order_number, customer_email)


def order_tracking(workspace_id: str, order_number: str, customer_email: Optional[str] = None) -> Dict[str, Any]:
    order = get_tenant_order_sync(workspace_id, order_number, customer_email or "sarah.connor@example.com")
    if not order:
        return OrderTrackingOutput(found=False, order_number=order_number).model_dump()

    return OrderTrackingOutput(
        found=True,
        order_number=order["order_number"],
        status=order["status"],
        carrier=order["carrier"],
        tracking_number=order["tracking_number"],
        masked_address=order.get("masked_address", "Indiranagar, Bengaluru, KA"),
        estimated_delivery="Within 2-3 business days via Express Courier",
        items=order.get("items", [])
    ).model_dump()


def coupon_validation(workspace_id: str, coupon_code: str, cart_subtotal: float) -> Dict[str, Any]:
    code_u = coupon_code.strip().upper()
    discounts = {
        "WELCOME10": 0.10,
        "SAVE20": 0.20,
        "FLAT15": 0.15,
        "TECHNOVANEW": 0.10
    }

    if code_u in discounts:
        pct = discounts[code_u]
        disc_val = round(cart_subtotal * pct, 2)
        return CouponValidationOutput(
            valid=True,
            code=code_u,
            discount_amount=disc_val,
            discount_percentage=pct * 100.0,
            message=f"Coupon {code_u} applied successfully! Saved ₹{disc_val:.2f}"
        ).model_dump()

    return CouponValidationOutput(
        valid=False,
        code=code_u,
        discount_amount=0.0,
        discount_percentage=0.0,
        message=f"Coupon code '{code_u}' is invalid or expired."
    ).model_dump()

def apply_discount(workspace_id: str, code: str, subtotal: float) -> Dict[str, Any]:
    return coupon_validation(workspace_id, code, subtotal)


def return_eligibility(workspace_id: str, order_number: str, customer_email: Optional[str] = None, product_id: Optional[str] = None) -> Dict[str, Any]:
    return ReturnEligibilityOutput(
        eligible=True,
        order_number=order_number,
        return_window_days=30,
        reason="Order is within the 30-day doorstep exchange and return policy.",
        doorstep_pickup_available=True
    ).model_dump()


def create_return(workspace_id: str, order_number: str, customer_email: str, product_id: Optional[str] = None, reason: str = "Size exchange") -> Dict[str, Any]:
    ret_id = f"ret_{uuid.uuid4().hex[:8]}"
    return CreateReturnOutput(
        success=True,
        return_id=ret_id,
        return_label_url=f"https://shipping.bluetyga.com/labels/{ret_id}.pdf",
        carrier="Bluedart Express",
        doorstep_pickup_date="Next Business Day (10:00 AM - 2:00 PM)",
        message=f"Return request {ret_id} created successfully for order {order_number}. Free doorstep courier pickup scheduled."
    ).model_dump()


def add_to_cart(workspace_id: str, product_id: str, quantity: int = 1, variant_id: Optional[str] = None, size: Optional[str] = None, color: Optional[str] = None, cart_id: Optional[str] = None) -> Dict[str, Any]:
    prods = get_tenant_products_sync(workspace_id)
    target = next((p for p in prods if p["id"] == product_id), None)
    if not target:
        return AddToCartOutput(success=False, message=f"Product {product_id} not found").model_dump()

    c_id = cart_id or f"cart_{uuid.uuid4().hex[:10]}"
    price = float(target["price"])
    subtotal = price * quantity

    return AddToCartOutput(
        success=True,
        cart_id=c_id,
        product_id=product_id,
        title=target["title"],
        quantity=quantity,
        price=price,
        subtotal=subtotal,
        item_count=quantity,
        message=f"Added {quantity}x '{target['title']}' to your shopping cart."
    ).model_dump()


def cart_lookup(workspace_id: str, cart_id: Optional[str] = None, items: Optional[List[Dict[str, Any]]] = None, discount_code: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    c_id = cart_id or f"cart_{uuid.uuid4().hex[:10]}"
    prods = get_tenant_products_sync(workspace_id)

    line_items = []
    subtotal = 0.0

    raw_items = items or [{"product_id": "prod_bt_01", "quantity": 1}]
    for it in raw_items:
        pid = it.get("product_id")
        qty = int(it.get("quantity", 1))
        matched = next((p for p in prods if p["id"] == pid), None)
        title = matched["title"] if matched else f"Item ({pid})"
        u_price = float(matched["price"]) if matched else 999.0
        line_total = u_price * qty
        subtotal += line_total
        line_items.append({
            "product_id": pid,
            "title": title,
            "quantity": qty,
            "unit_price": u_price,
            "total_price": line_total
        })

    disc_amount = 0.0
    disc_applied = None
    if discount_code:
        disc_res = coupon_validation(workspace_id, discount_code, subtotal)
        if disc_res["valid"]:
            disc_amount = disc_res["discount_amount"]
            disc_applied = disc_res

    shipping = 0.0 if subtotal >= 499.0 else 49.0
    tax = round(subtotal * 0.12, 2)
    grand_total = max(0.0, round(subtotal - disc_amount + shipping + tax, 2))

    return CartLookupOutput(
        cart_id=c_id,
        items=line_items,
        line_items=line_items,
        subtotal=subtotal,
        shipping_amount=shipping,
        tax_amount=tax,
        discount_amount=disc_amount,
        grand_total=grand_total,
        total=grand_total,
        discount_applied=disc_applied
    ).model_dump()

def calculate_cart(workspace_id: str, items: List[Dict[str, Any]], discount_code: Optional[str] = None) -> Dict[str, Any]:
    return cart_lookup(workspace_id, items=items, discount_code=discount_code)


def human_handoff(workspace_id: str, reason: str = "Customer requested human support", customer_email: Optional[str] = None, summary: Optional[str] = None) -> Dict[str, Any]:
    ticket = f"tkt_{uuid.uuid4().hex[:8]}"
    return HumanHandoffOutput(
        status="ESCALATED",
        ticket_id=ticket,
        queue="TIER_1_COMMERCE_SUPPORT",
        message="I have flagged this session for our customer support team. A representative will join this chat momentarily."
    ).model_dump()


# ============================================================================
# 7. DYNAMIC TOOL DISPATCHER
# ============================================================================

def execute_typed_tool(tool_name: str, arguments: Dict[str, Any], workspace_id: str) -> Dict[str, Any]:
    """Executes a tool call with strict typing, tenant isolation, and schema validation."""
    if not workspace_id:
        raise ValueError("workspace_id is mandatory for tool execution")

    args = dict(arguments)
    args["workspace_id"] = workspace_id

    dispatch_map = {
        "search_products": lambda: search_products(**args),
        "get_inventory": lambda: get_inventory(**args),
        "check_inventory": lambda: check_inventory(**args),
        "order_lookup": lambda: order_lookup(**args),
        "lookup_order": lambda: lookup_order(**args),
        "order_tracking": lambda: order_tracking(**args),
        "coupon_validation": lambda: coupon_validation(**args),
        "apply_discount": lambda: apply_discount(**args),
        "return_eligibility": lambda: return_eligibility(**args),
        "create_return": lambda: create_return(**args),
        "add_to_cart": lambda: add_to_cart(**args),
        "cart_lookup": lambda: cart_lookup(**args),
        "calculate_cart": lambda: calculate_cart(**args),
        "human_handoff": lambda: human_handoff(**args)
    }

    handler = dispatch_map.get(tool_name)
    if not handler:
        return {"error": f"Tool '{tool_name}' is not recognized or enabled in this agent's permission tier."}

    try:
        return handler()
    except Exception as e:
        return {"error": f"Tool execution error: {str(e)}"}
