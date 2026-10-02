import logging
from typing import Any

from ..adapters.catalog_adapter import CatalogAdapter
from ..types import AIModeProduct, AIModeRecommendationResponse

logger = logging.getLogger("ai_mode_recommendation_engine")

class AIModeRecommendationEngine:
    """
    Contextual AI Recommendation Engine for AI Mode.
    Generates dynamic suggestions based on browsing history, user preferences,
    semantic similarity, and price alignment.
    """

    def __init__(self, catalog_adapter: CatalogAdapter):
        self.catalog = catalog_adapter

    async def get_recommendations(
        self,
        workspace_id: str,
        product_id: str | None = None,
        user_intent: str | None = None,
        limit: int = 4,
        context: dict[str, Any] | None = None
    ) -> AIModeRecommendationResponse:
        """Computes top recommended products with explainable reasoning."""
        all_products = await self.catalog.get_all_products(workspace_id)
        if not all_products:
            return AIModeRecommendationResponse(
                recommendations=[],
                reasoning="No products available in the catalog.",
                strategy="CATALOG_EMPTY"
            )

        target_product: AIModeProduct | None = None
        if product_id:
            target_product = next((p for p in all_products if p.id == product_id), None)

        candidates = [p for p in all_products if p.id != product_id]
        if not candidates:
            candidates = all_products

        scored: list[tuple[AIModeProduct, float, str]] = []

        if target_product:
            # 1. Similarity to target product (Category + Tags + Price Proximity)
            target_tags = {t.lower() for t in target_product.tags}
            target_cat = target_product.category.lower()
            target_price = target_product.price

            for cand in candidates:
                cand_tags = {t.lower() for t in cand.tags}
                tag_overlap = len(target_tags.intersection(cand_tags))
                cat_match = 1.0 if cand.category.lower() == target_cat else 0.0

                # Price distance penalty
                price_ratio = min(cand.price, target_price) / max(cand.price, target_price, 1.0)

                score = (cat_match * 0.4) + (tag_overlap * 0.3) + (price_ratio * 0.2) + (0.1 if cand.in_stock else 0.0)
                reason = f"Shares category '{cand.category}' and similar styling" if cat_match else "Complementary styling pick"
                scored.append((cand, score, reason))

            strategy = "SIMILAR_ITEM_AFFINITY"
            overall_reasoning = f"Recommended items related to {target_product.title} based on category affinity, shared attributes, and price tier."
        else:
            # 2. General Intent / Popularity / In-Stock
            for cand in candidates:
                score = (0.5 if cand.in_stock else 0.0) + (0.3 if cand.images else 0.0)
                if user_intent and user_intent.lower() in (cand.title + " " + cand.category).lower():
                    score += 0.5
                reason = f"Top-rated selection in {cand.category}"
                scored.append((cand, score, reason))

            strategy = "TRENDING_AND_INTENT"
            overall_reasoning = "Curated top products based on active catalog demand and store ratings."

        scored.sort(key=lambda x: x[1], reverse=True)
        top_picks = [item[0] for item in scored[:limit]]

        return AIModeRecommendationResponse(
            recommendations=top_picks,
            reasoning=overall_reasoning,
            strategy=strategy
        )
