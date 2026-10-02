import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import KnowledgeChunkModel
from ..db_models import AIModeKnowledgeChunkModel

logger = logging.getLogger("ai_mode_knowledge_adapter")

class KnowledgeAdapter:
    """
    Safe Adapter to read knowledge base information.
    Can query existing knowledge sources / docs / chunks without mutating them,
    as well as AI Mode specific knowledge collections.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_combined_knowledge_context(self, workspace_id: str, query_tokens: list[str], top_k: int = 4) -> list[dict[str, Any]]:
        """
        Retrieves relevant factual knowledge snippets from both AI Mode knowledge base
        and existing store knowledge sources.
        """
        snippets: list[dict[str, Any]] = []
        try:
            # 1. Fetch from AI Mode Knowledge Chunks
            stmt_ai = select(AIModeKnowledgeChunkModel).where(
                AIModeKnowledgeChunkModel.workspace_id == workspace_id
            ).limit(20)
            res_ai = await self.session.execute(stmt_ai)
            ai_chunks = res_ai.scalars().all()

            for c in ai_chunks:
                text_lower = c.text.lower()
                matches = sum(1 for t in query_tokens if t in text_lower)
                if matches > 0:
                    snippets.append({
                        "source": "ai_mode_knowledge",
                        "title": c.metadata_json.get("title", "Store FAQ & Policy") if isinstance(c.metadata_json, dict) else "Store FAQ",
                        "content": c.text,
                        "score": float(matches)
                    })

            # 2. Fetch from Existing Platform Knowledge Chunks (Read-only)
            stmt_std = select(KnowledgeChunkModel).where(
                KnowledgeChunkModel.workspace_id == workspace_id
            ).limit(20)
            res_std = await self.session.execute(stmt_std)
            std_chunks = res_std.scalars().all()

            for c in std_chunks:
                text_lower = c.text.lower()
                matches = sum(1 for t in query_tokens if t in text_lower)
                if matches > 0:
                    snippets.append({
                        "source": "store_knowledge",
                        "title": c.metadata_json.get("title", "General Knowledge") if isinstance(c.metadata_json, dict) else "General Knowledge",
                        "content": c.text,
                        "score": float(matches)
                    })

            # Sort by score descending and take top_k
            snippets.sort(key=lambda x: x.get("score", 0), reverse=True)
            return snippets[:top_k]
        except Exception as e:
            logger.error(f"KnowledgeAdapter failed to fetch combined context: {e}")
            return []
