import datetime
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.cart_adapter import CartAdapter
from ..adapters.catalog_adapter import CatalogAdapter
from ..adapters.knowledge_adapter import KnowledgeAdapter
from ..db_models import AIModeConversationModel, AIModeMessageModel
from ..types import AIModeChatResponse
from .comparison_engine import AIModeComparisonEngine
from .search_engine import AIModeSearchEngine

logger = logging.getLogger("ai_mode_conversation_service")

class AIModeConversationService:
    """
    Conversational Shopping & Multi-Turn Reasoning Service for AI Mode.
    Maintains dialogue state, resolves follow-ups, queries knowledge,
    and returns authoritative product recommendations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.catalog = CatalogAdapter(session)
        self.cart = CartAdapter(session)
        self.knowledge = KnowledgeAdapter(session)
        self.search_engine = AIModeSearchEngine(self.catalog)
        self.comparison_engine = AIModeComparisonEngine(self.catalog)

    async def get_or_create_conversation(
        self,
        workspace_id: str,
        conversation_id: str | None = None,
        session_id: str | None = None,
        channel: str = "PREVIEW"
    ) -> AIModeConversationModel:
        """Fetch or initialize persistent conversation state."""
        if conversation_id:
            stmt = select(AIModeConversationModel).where(
                AIModeConversationModel.workspace_id == workspace_id,
                AIModeConversationModel.id == conversation_id
            )
            res = await self.session.execute(stmt)
            conv = res.scalar_one_or_none()
            if conv:
                return conv

        new_id = conversation_id or f"aimc_{uuid.uuid4().hex[:12]}"
        conv = AIModeConversationModel(
            id=new_id,
            workspace_id=workspace_id,
            session_id=session_id or f"sess_{uuid.uuid4().hex[:8]}",
            channel=channel,
            title="AI Shopping Session",
            last_search_state={},
            context_json={},
            created_at=datetime.datetime.now(datetime.UTC),
            updated_at=datetime.datetime.now(datetime.UTC)
        )
        self.session.add(conv)
        await self.session.flush()
        return conv

    async def process_chat(
        self,
        workspace_id: str,
        message: str,
        conversation_id: str | None = None,
        session_id: str | None = None,
        customer_email: str | None = None,
        channel: str = "PREVIEW",
        context: dict[str, Any] | None = None
    ) -> AIModeChatResponse:
        """
        Main multi-turn conversational loop.
        Evaluates user message against conversation history, knowledge base,
        and merchant catalog.
        """
        conv = await self.get_or_create_conversation(workspace_id, conversation_id, session_id, channel)
        conv_context = conv.context_json or {}
        last_search = conv.last_search_state or {}

        msg_lower = message.strip().lower()

        # Record user message in DB
        u_msg_id = f"aimm_{uuid.uuid4().hex[:10]}"
        user_msg = AIModeMessageModel(
            id=u_msg_id,
            workspace_id=workspace_id,
            conversation_id=conv.id,
            sender="USER",
            content=message,
            intent="USER_QUERY",
            metadata_json={"channel": channel, "customer_email": customer_email},
            created_at=datetime.datetime.now(datetime.UTC)
        )
        self.session.add(user_msg)

        # 1. Check for Add to Cart intent
        if any(w in msg_lower for w in ["add to cart", "buy this", "add the first", "add second", "add this"]):
            target_prod_id = None
            last_prods = last_search.get("product_ids", [])

            if "first" in msg_lower and len(last_prods) >= 1:
                target_prod_id = last_prods[0]
            elif "second" in msg_lower and len(last_prods) >= 2:
                target_prod_id = last_prods[1]
            elif len(last_prods) == 1:
                target_prod_id = last_prods[0]

            if target_prod_id:
                cart_res = await self.cart.add_item_to_cart(
                    workspace_id=workspace_id,
                    session_id=conv.session_id or f"sess_{conv.id}",
                    product_id=target_prod_id,
                    quantity=1
                )
                if cart_res.get("success"):
                    prod_info = cart_res["added_product"]
                    reply = f"🛒 Added **{prod_info['title']}** ({prod_info['price']} INR) to your shopping cart! You have {cart_res['total_items']} items in your cart."
                    return await self._save_and_return_response(
                        workspace_id, conv, reply, "ADD_TO_CART", [], None, ["View Cart", "Proceed to Checkout", "Show similar items"]
                    )

        # 2. Check for Comparison Intent
        if any(w in msg_lower for w in ["compare", "vs", "difference", "which is better"]):
            last_prods = last_search.get("product_ids", [])
            if len(last_prods) >= 2:
                comp_res = await self.comparison_engine.compare_products(workspace_id, last_prods[:3], message)
                return await self._save_and_return_response(
                    workspace_id, conv, comp_res.ai_summary, "COMPARISON", comp_res.products, comp_res.model_dump(), ["Show cheaper options", "Add to cart", "Check shipping policy"]
                )

        # 3. Check for Knowledge / Policy Question
        tokens = [t for t in msg_lower.split() if len(t) > 3]
        knowledge_hits = await self.knowledge.get_combined_knowledge_context(workspace_id, tokens, top_k=2)

        # 4. Check for Pagination / "Show more"
        current_page = 1
        if "show more" in msg_lower or "next page" in msg_lower or "more options" in msg_lower:
            current_page = last_search.get("page", 1) + 1
            query_to_run = last_search.get("query", message)
        else:
            query_to_run = message

        # 5. Execute AI Mode Search Engine
        search_res = await self.search_engine.execute_search(
            workspace_id=workspace_id,
            query=query_to_run,
            page=current_page,
            page_size=6,
            conversation_context=conv_context
        )

        # Update Conversation State
        if search_res.products:
            conv.last_search_state = {
                "query": query_to_run,
                "page": current_page,
                "product_ids": [p.id for p in search_res.products],
                "last_min_price": min(p.price for p in search_res.products),
                "total_matches": search_res.total_matches
            }
            conv.context_json = {
                "last_intent": search_res.search_plan.get("intent", "DISCOVERY"),
                "last_query": query_to_run
            }

        # Synthesize Response Text
        reply_parts: list[str] = []
        if knowledge_hits and ("return" in msg_lower or "policy" in msg_lower or "shipping" in msg_lower or "exchange" in msg_lower or "warranty" in msg_lower):
            reply_parts.append(f"📋 **Store Information:** {knowledge_hits[0]['content']}")

        if search_res.products:
            reply_parts.append(search_res.ai_summary)
        elif not reply_parts:
            reply_parts.append(f"I couldn't find any products matching '{message}'. Let me know what you're looking for or check out our categories!")

        final_reply = "\n\n".join(reply_parts)
        pagination_info = {
            "page": current_page,
            "page_size": 6,
            "total_matches": search_res.total_matches,
            "has_more": search_res.has_more
        }

        return await self._save_and_return_response(
            workspace_id=workspace_id,
            conv=conv,
            reply=final_reply,
            intent=search_res.search_plan.get("intent", "DISCOVERY"),
            products=search_res.products,
            comparison_matrix=None,
            suggestions=search_res.suggestions,
            pagination=pagination_info,
            search_plan=search_res.search_plan
        )

    async def _save_and_return_response(
        self,
        workspace_id: str,
        conv: AIModeConversationModel,
        reply: str,
        intent: str,
        products: list[Any],
        comparison_matrix: dict[str, Any] | None,
        suggestions: list[str],
        pagination: dict[str, Any] | None = None,
        search_plan: dict[str, Any] | None = None
    ) -> AIModeChatResponse:
        """Records assistant message and commits state."""
        a_msg_id = f"aimm_{uuid.uuid4().hex[:10]}"
        prods_data = [p.model_dump() if hasattr(p, "model_dump") else p for p in products]

        assistant_msg = AIModeMessageModel(
            id=a_msg_id,
            workspace_id=workspace_id,
            conversation_id=conv.id,
            sender="ASSISTANT",
            content=reply,
            intent=intent,
            products_json=prods_data,
            comparison_json=comparison_matrix,
            metadata_json={"suggestions": suggestions, "pagination": pagination},
            created_at=datetime.datetime.now(datetime.UTC)
        )
        self.session.add(assistant_msg)
        conv.updated_at = datetime.datetime.now(datetime.UTC)
        await self.session.commit()

        return AIModeChatResponse(
            conversation_id=conv.id,
            message_id=a_msg_id,
            response=reply,
            intent=intent,
            products=products,
            comparison_matrix=comparison_matrix,
            suggestions=suggestions,
            pagination=pagination,
            search_plan=search_plan,
            status="SUCCESS"
        )
