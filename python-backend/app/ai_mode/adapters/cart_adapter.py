import datetime
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import CartModel, ProductModel

logger = logging.getLogger("ai_mode_cart_adapter")

class CartAdapter:
    """
    Safe Adapter to interact with the merchant cart.
    Allows AI Mode to perform Add-to-Cart and Cart-Inspection without
    modifying underlying cart schema or mechanics.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_cart(self, workspace_id: str, session_id: str) -> dict[str, Any]:
        """Fetch active cart for a session or initialize a new one."""
        try:
            stmt = select(CartModel).where(
                CartModel.workspace_id == workspace_id,
                CartModel.session_id == session_id
            )
            result = await self.session.execute(stmt)
            cart = result.scalar_one_or_none()
            if not cart:
                cart = CartModel(
                    id=f"cart_{session_id[-8:]}",
                    workspace_id=workspace_id,
                    session_id=session_id,
                    items_json=[],
                    subtotal=0.0,
                    discounts_json={},
                    created_at=datetime.datetime.now(datetime.UTC),
                    updated_at=datetime.datetime.now(datetime.UTC)
                )
                self.session.add(cart)
                await self.session.flush()

            items = cart.items_json if isinstance(cart.items_json, list) else []
            return {
                "id": cart.id,
                "session_id": cart.session_id,
                "items": items,
                "item_count": sum(it.get("quantity", 1) for it in items),
                "subtotal": float(cart.subtotal or 0.0),
                "currency": "INR"
            }
        except Exception as e:
            logger.error(f"CartAdapter get_or_create_cart failed: {e}")
            return {"id": "cart_fallback", "session_id": session_id, "items": [], "item_count": 0, "subtotal": 0.0, "currency": "INR"}

    async def add_item_to_cart(
        self,
        workspace_id: str,
        session_id: str,
        product_id: str,
        quantity: int = 1,
        variant_id: str | None = None
    ) -> dict[str, Any]:
        """Safely add a verified product to the session cart."""
        try:
            # 1. Look up authoritative product details
            p_stmt = select(ProductModel).where(
                ProductModel.workspace_id == workspace_id,
                ProductModel.id == product_id
            )
            p_res = await self.session.execute(p_stmt)
            product = p_res.scalar_one_or_none()
            if not product:
                return {"success": False, "error": f"Product '{product_id}' not found in catalog."}

            # 2. Look up or create cart
            c_stmt = select(CartModel).where(
                CartModel.workspace_id == workspace_id,
                CartModel.session_id == session_id
            )
            c_res = await self.session.execute(c_stmt)
            cart = c_res.scalar_one_or_none()
            if not cart:
                cart = CartModel(
                    id=f"cart_{session_id[-8:]}",
                    workspace_id=workspace_id,
                    session_id=session_id,
                    items_json=[],
                    subtotal=0.0,
                    discounts_json={},
                    created_at=datetime.datetime.now(datetime.UTC),
                    updated_at=datetime.datetime.now(datetime.UTC)
                )
                self.session.add(cart)

            items = list(cart.items_json) if isinstance(cart.items_json, list) else []
            existing_idx = next((i for i, it in enumerate(items) if it.get("product_id") == product_id and it.get("variant_id") == variant_id), None)

            price = float(product.price)
            if existing_idx is not None:
                items[existing_idx]["quantity"] = items[existing_idx].get("quantity", 1) + quantity
            else:
                img = product.images[0] if product.images and isinstance(product.images, list) else ""
                items.append({
                    "product_id": product.id,
                    "title": product.title,
                    "price": price,
                    "quantity": quantity,
                    "image": img,
                    "variant_id": variant_id
                })

            cart.items_json = items
            cart.subtotal = sum(float(it.get("price", 0.0)) * int(it.get("quantity", 1)) for it in items)
            cart.updated_at = datetime.datetime.now(datetime.UTC)
            await self.session.commit()

            return {
                "success": True,
                "cart_id": cart.id,
                "added_product": {
                    "id": product.id,
                    "title": product.title,
                    "price": price,
                    "quantity": quantity
                },
                "total_items": sum(it.get("quantity", 1) for it in items),
                "subtotal": cart.subtotal
            }
        except Exception as e:
            logger.error(f"CartAdapter add_item_to_cart error: {e}")
            return {"success": False, "error": str(e)}
