import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import ProductModel
from ..types import AIModeProduct

logger = logging.getLogger("ai_mode_catalog_adapter")

class CatalogAdapter:
    """
    Safe Read-Only Adapter for the existing store catalog.
    Strictly preserves product boundaries and all authoritative fields
    (name, URL, description, price, images, availability, variants, categories, metadata).
    NEVER mutates or writes to existing catalog tables.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_products(self, workspace_id: str) -> list[AIModeProduct]:
        """Fetch all products for a workspace converted into safe AIModeProduct instances."""
        try:
            stmt = select(ProductModel).where(ProductModel.workspace_id == workspace_id)
            result = await self.session.execute(stmt)
            rows = result.scalars().all()
            return [self._to_ai_mode_product(p) for p in rows]
        except Exception as e:
            logger.error(f"CatalogAdapter failed to fetch products for workspace {workspace_id}: {e}")
            return []

    async def get_product_by_id(self, workspace_id: str, product_id: str) -> AIModeProduct | None:
        """Fetch a single authoritative product by ID."""
        try:
            stmt = select(ProductModel).where(
                ProductModel.workspace_id == workspace_id,
                ProductModel.id == product_id
            )
            result = await self.session.execute(stmt)
            p = result.scalar_one_or_none()
            if p:
                return self._to_ai_mode_product(p)
            return None
        except Exception as e:
            logger.error(f"CatalogAdapter failed to fetch product {product_id}: {e}")
            return None

    async def get_products_by_ids(self, workspace_id: str, product_ids: list[str]) -> list[AIModeProduct]:
        """Fetch multiple authoritative products by their IDs."""
        if not product_ids:
            return []
        try:
            stmt = select(ProductModel).where(
                ProductModel.workspace_id == workspace_id,
                ProductModel.id.in_(product_ids)
            )
            result = await self.session.execute(stmt)
            rows = result.scalars().all()
            return [self._to_ai_mode_product(p) for p in rows]
        except Exception as e:
            logger.error(f"CatalogAdapter failed to fetch products by ids: {e}")
            return []

    def _to_ai_mode_product(self, p: ProductModel) -> AIModeProduct:
        """Transform SQLAlchemy ProductModel into immutable AIModeProduct."""
        images = p.images if isinstance(p.images, list) else []
        tags = p.tags if isinstance(p.tags, list) else []
        variants = p.variants_json if isinstance(p.variants_json, list) else []
        attributes = p.attributes_json if isinstance(p.attributes_json, dict) else {}

        # Build dynamic highlights from attributes / tags
        highlights: list[str] = []
        if tags:
            highlights.extend(tags[:3])
        for k, v in attributes.items():
            if isinstance(v, (str, int, float)) and len(highlights) < 5:
                highlights.append(f"{k.capitalize()}: {v}")

        return AIModeProduct(
            id=p.id,
            title=p.title,
            description=p.description or "",
            price=float(p.price),
            compare_at_price=float(p.compare_at_price) if p.compare_at_price is not None else None,
            currency=p.currency or "INR",
            category=p.category or "General",
            tags=tags,
            images=images,
            in_stock=bool(p.in_stock),
            total_inventory=int(p.total_inventory or 0),
            source_url=p.source_url,
            attributes=attributes,
            variants=variants,
            highlights=highlights
        )
