import datetime
import logging
import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.crawler_adapter import CrawlerAdapter
from ..db_models import (
    AIModeKnowledgeChunkModel,
    AIModeKnowledgeDocModel,
    AIModeKnowledgeModel,
)

logger = logging.getLogger("ai_mode_knowledge_service")

class AIModeKnowledgeService:
    """
    Dedicated Knowledge Management Service for AI Mode.
    Supports Website Crawlers, File Uploads, FAQs, and Business Information.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_sources(self, workspace_id: str) -> list[dict[str, Any]]:
        """List all AI Mode knowledge sources for a workspace."""
        stmt = select(AIModeKnowledgeModel).where(
            AIModeKnowledgeModel.workspace_id == workspace_id
        ).order_by(AIModeKnowledgeModel.created_at.desc())
        res = await self.session.execute(stmt)
        sources = res.scalars().all()

        return [
            {
                "id": s.id,
                "name": s.name,
                "source_type": s.source_type,
                "status": s.status,
                "document_count": s.document_count,
                "chunk_count": s.chunk_count,
                "error_message": s.error_message,
                "last_synced_at": s.last_synced_at.isoformat() if s.last_synced_at else None,
                "config": s.config_json or {},
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in sources
        ]

    async def create_source(
        self,
        workspace_id: str,
        name: str,
        source_type: str,
        config: dict[str, Any],
        raw_content: str | None = None
    ) -> dict[str, Any]:
        """Creates a knowledge source and kicks off synchronous/background ingestion."""
        source_id = f"aimk_{uuid.uuid4().hex[:12]}"
        source = AIModeKnowledgeModel(
            id=source_id,
            workspace_id=workspace_id,
            name=name,
            source_type=source_type,
            status="SYNCING",
            document_count=0,
            chunk_count=0,
            config_json=config,
            created_at=datetime.datetime.now(datetime.UTC),
            updated_at=datetime.datetime.now(datetime.UTC)
        )
        self.session.add(source)
        await self.session.flush()

        # Ingest content based on source_type
        try:
            doc_count, chunk_count = await self._ingest_source_data(source, raw_content)
            source.status = "READY"
            source.document_count = doc_count
            source.chunk_count = chunk_count
            source.last_synced_at = datetime.datetime.now(datetime.UTC)
            source.error_message = None
        except Exception as e:
            logger.error(f"Failed to ingest knowledge source {source_id}: {e}")
            source.status = "ERROR"
            source.error_message = str(e)

        await self.session.commit()
        return {
            "id": source.id,
            "name": source.name,
            "source_type": source.source_type,
            "status": source.status,
            "document_count": source.document_count,
            "chunk_count": source.chunk_count,
            "error_message": source.error_message
        }

    async def sync_source(self, workspace_id: str, source_id: str) -> dict[str, Any]:
        """Re-syncs an existing knowledge source."""
        stmt = select(AIModeKnowledgeModel).where(
            AIModeKnowledgeModel.workspace_id == workspace_id,
            AIModeKnowledgeModel.id == source_id
        )
        res = await self.session.execute(stmt)
        source = res.scalar_one_or_none()
        if not source:
            raise ValueError(f"Knowledge source '{source_id}' not found.")

        # Delete previous documents and chunks
        await self.session.execute(
            delete(AIModeKnowledgeDocModel).where(
                AIModeKnowledgeDocModel.workspace_id == workspace_id,
                AIModeKnowledgeDocModel.source_id == source_id
            )
        )

        source.status = "SYNCING"
        await self.session.flush()

        try:
            doc_count, chunk_count = await self._ingest_source_data(source, None)
            source.status = "READY"
            source.document_count = doc_count
            source.chunk_count = chunk_count
            source.last_synced_at = datetime.datetime.now(datetime.UTC)
            source.error_message = None
        except Exception as e:
            logger.error(f"Failed to sync source {source_id}: {e}")
            source.status = "ERROR"
            source.error_message = str(e)

        await self.session.commit()
        return {
            "id": source.id,
            "name": source.name,
            "status": source.status,
            "document_count": source.document_count,
            "chunk_count": source.chunk_count,
            "error_message": source.error_message
        }

    async def delete_source(self, workspace_id: str, source_id: str) -> bool:
        """Deletes a knowledge source and all attached documents/chunks."""
        stmt = select(AIModeKnowledgeModel).where(
            AIModeKnowledgeModel.workspace_id == workspace_id,
            AIModeKnowledgeModel.id == source_id
        )
        res = await self.session.execute(stmt)
        source = res.scalar_one_or_none()
        if not source:
            return False

        await self.session.delete(source)
        await self.session.commit()
        return True

    async def _ingest_source_data(self, source: AIModeKnowledgeModel, raw_content: str | None) -> tuple[int, int]:
        """Internal processor for URL crawling, FAQs, files, and text."""
        config = source.config_json or {}
        docs_created = 0
        chunks_created = 0

        if source.source_type == "URL_CRAWLER":
            url = config.get("url")
            if not url:
                raise ValueError("Website URL is required for URL_CRAWLER source.")
            extracted = CrawlerAdapter.fetch_and_extract_url(url)
            doc_id = f"doc_{uuid.uuid4().hex[:10]}"
            doc = AIModeKnowledgeDocModel(
                id=doc_id,
                workspace_id=source.workspace_id,
                source_id=source.id,
                title=extracted["title"],
                content=extracted["text"],
                url=url,
                doc_type="WEBSITE_PAGE",
                metadata_json={"url": url, "paragraphs_count": len(extracted["paragraphs"])},
                created_at=datetime.datetime.now(datetime.UTC)
            )
            self.session.add(doc)
            docs_created += 1

            for idx, p in enumerate(extracted["paragraphs"]):
                c_id = f"chk_{uuid.uuid4().hex[:10]}"
                chunk = AIModeKnowledgeChunkModel(
                    id=c_id,
                    workspace_id=source.workspace_id,
                    doc_id=doc_id,
                    chunk_index=idx,
                    text=p,
                    embedding=[0.0] * 128,
                    metadata_json={"source": url, "title": extracted["title"]},
                    created_at=datetime.datetime.now(datetime.UTC)
                )
                self.session.add(chunk)
                chunks_created += 1

        elif source.source_type in ("FILE_UPLOAD", "BUSINESS_INFO", "FAQ"):
            content = raw_content or config.get("content") or ""
            if not content:
                content = f"Knowledge information for {source.name}"

            doc_id = f"doc_{uuid.uuid4().hex[:10]}"
            doc = AIModeKnowledgeDocModel(
                id=doc_id,
                workspace_id=source.workspace_id,
                source_id=source.id,
                title=source.name,
                content=content,
                doc_type=source.source_type,
                metadata_json=config,
                created_at=datetime.datetime.now(datetime.UTC)
            )
            self.session.add(doc)
            docs_created += 1

            paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 15]
            if not paragraphs:
                paragraphs = [content]

            for idx, p in enumerate(paragraphs):
                c_id = f"chk_{uuid.uuid4().hex[:10]}"
                chunk = AIModeKnowledgeChunkModel(
                    id=c_id,
                    workspace_id=source.workspace_id,
                    doc_id=doc_id,
                    chunk_index=idx,
                    text=p,
                    embedding=[0.0] * 128,
                    metadata_json={"source_name": source.name, "type": source.source_type},
                    created_at=datetime.datetime.now(datetime.UTC)
                )
                self.session.add(chunk)
                chunks_created += 1

        return docs_created, chunks_created
