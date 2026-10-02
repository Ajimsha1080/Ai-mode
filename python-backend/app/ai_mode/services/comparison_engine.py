import logging
from typing import Any

from ..adapters.catalog_adapter import CatalogAdapter
from ..types import AIModeCompareResponse

logger = logging.getLogger("ai_mode_comparison_engine")

class AIModeComparisonEngine:
    """
    AI Mode Product Comparison Engine.
    Performs authoritative, side-by-side comparisons using merchant data only.
    Never hallucinates specifications; clearly marks missing info as 'Information not available'.
    """

    def __init__(self, catalog_adapter: CatalogAdapter):
        self.catalog = catalog_adapter

    async def compare_products(
        self,
        workspace_id: str,
        product_ids: list[str],
        user_query: str | None = None
    ) -> AIModeCompareResponse:
        """Compares up to 4 products and builds a structured comparison matrix."""
        products = await self.catalog.get_products_by_ids(workspace_id, product_ids[:4])

        if not products:
            return AIModeCompareResponse(
                products=[],
                comparison_table=[],
                ai_summary="None of the selected products could be found in the catalog.",
                best_for={},
                verdict="Please select valid products from the store to compare."
            )

        if len(products) == 1:
            p = products[0]
            return AIModeCompareResponse(
                products=products,
                comparison_table=[
                    {"feature": "Price", p.title: f"{p.currency} {p.price:,.2f}"},
                    {"feature": "Availability", p.title: "In Stock" if p.in_stock else "Out of Stock"},
                    {"feature": "Category", p.title: p.category}
                ],
                ai_summary=f"Selected only {p.title}. Add another product to see a side-by-side comparison.",
                best_for={p.id: "Single selected product"},
                verdict=f"{p.title} is available at {p.currency} {p.price:,.2f}."
            )

        # Build Comparison Rows
        # 1. Price
        price_row: dict[str, Any] = {"feature": "Price"}
        # 2. Availability
        stock_row: dict[str, Any] = {"feature": "Stock Status"}
        # 3. Category
        cat_row: dict[str, Any] = {"feature": "Category"}
        # 4. Inventory
        inv_row: dict[str, Any] = {"feature": "Inventory"}

        # Collect union of all attribute keys across products
        all_attr_keys: set[str] = set()
        for p in products:
            price_row[p.title] = f"{p.currency} {p.price:,.2f}"
            stock_row[p.title] = "In Stock" if p.in_stock else "Out of Stock"
            cat_row[p.title] = p.category
            inv_row[p.title] = f"{p.total_inventory} units" if p.total_inventory > 0 else "Limited"
            for k in p.attributes.keys():
                all_attr_keys.add(k)

        table: list[dict[str, Any]] = [price_row, stock_row, cat_row, inv_row]

        # Dynamic attribute rows
        for attr_key in sorted(all_attr_keys):
            row: dict[str, Any] = {"feature": attr_key.replace("_", " ").capitalize()}
            for p in products:
                val = p.attributes.get(attr_key)
                if val is not None and str(val).strip():
                    row[p.title] = str(val)
                else:
                    row[p.title] = "Information not available"
            table.append(row)

        # Build "Best For" & Verdict
        best_for: dict[str, str] = {}
        cheapest_prod = min(products, key=lambda x: x.price)
        priciest_prod = max(products, key=lambda x: x.price)

        for p in products:
            if p.id == cheapest_prod.id:
                best_for[p.id] = "Best value / Budget-friendly"
            elif p.id == priciest_prod.id:
                best_for[p.id] = "Premium choice / Maximum features"
            else:
                best_for[p.id] = f"Great balance in {p.category}"

        titles_str = " vs ".join(p.title for p in products)
        ai_summary = f"Comparing {titles_str}. {cheapest_prod.title} offers the lowest price at {cheapest_prod.currency} {cheapest_prod.price:,.2f}, while {priciest_prod.title} is the premium option at {priciest_prod.currency} {priciest_prod.price:,.2f}."
        verdict = f"Choose {cheapest_prod.title} if price is your top priority, or {priciest_prod.title} for enhanced specifications."

        return AIModeCompareResponse(
            products=products,
            comparison_table=table,
            ai_summary=ai_summary,
            best_for=best_for,
            verdict=verdict
        )
