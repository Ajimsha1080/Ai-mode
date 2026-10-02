import datetime
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db_models import AIModeDeploymentModel

logger = logging.getLogger("ai_mode_deployment_service")

class AIModeDeploymentService:
    """
    Dedicated Deployment Service for AI Mode Website Widgets.
    Completely decoupled and isolated from any existing widget deployments.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_deployments(self, workspace_id: str) -> list[dict[str, Any]]:
        """List all AI Mode deployments for a workspace."""
        stmt = select(AIModeDeploymentModel).where(
            AIModeDeploymentModel.workspace_id == workspace_id
        ).order_by(AIModeDeploymentModel.created_at.desc())
        res = await self.session.execute(stmt)
        deps = res.scalars().all()

        return [self._format_deployment(d) for d in deps]

    async def create_deployment(
        self,
        workspace_id: str,
        name: str = "AI Mode Widget",
        allowed_domains: list[str] | None = None,
        theme_config: dict[str, Any] | None = None,
        welcome_message: str = "Hi! 👋 Welcome to our AI Store. What can I find for you today?",
        launcher_text: str = "Ask AI Mode"
    ) -> dict[str, Any]:
        """Creates a new independent AI Mode deployment."""
        public_widget_id = f"aim_pub_{uuid.uuid4().hex[:16]}"
        dep_id = f"aimd_{uuid.uuid4().hex[:12]}"

        default_theme = {
            "primaryColor": "#6366f1",
            "themeMode": "light",
            "position": "bottom_right",
            "launcherShape": "pill",
            "launcherIcon": "sparkles",
            "starterQuestions": [
                "Find trending products",
                "Show items under ₹1,000",
                "Compare top selections",
                "What is your exchange policy?"
            ]
        }
        if theme_config:
            default_theme.update(theme_config)

        dep = AIModeDeploymentModel(
            id=dep_id,
            workspace_id=workspace_id,
            name=name,
            public_widget_id=public_widget_id,
            status="ACTIVE",
            allowed_domains=allowed_domains or ["*"],
            theme_config=default_theme,
            welcome_message=welcome_message,
            launcher_text=launcher_text,
            created_at=datetime.datetime.now(datetime.UTC),
            updated_at=datetime.datetime.now(datetime.UTC)
        )
        self.session.add(dep)
        await self.session.commit()
        return self._format_deployment(dep)

    async def update_deployment(
        self,
        workspace_id: str,
        deployment_id: str,
        updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Updates AI Mode deployment settings."""
        stmt = select(AIModeDeploymentModel).where(
            AIModeDeploymentModel.workspace_id == workspace_id,
            AIModeDeploymentModel.id == deployment_id
        )
        res = await self.session.execute(stmt)
        dep = res.scalar_one_or_none()
        if not dep:
            return None

        if "name" in updates and updates["name"] is not None:
            dep.name = updates["name"]
        if "status" in updates and updates["status"] is not None:
            dep.status = updates["status"]
        if "allowed_domains" in updates and updates["allowed_domains"] is not None:
            dep.allowed_domains = updates["allowed_domains"]
        if "theme_config" in updates and updates["theme_config"] is not None:
            current_theme = dict(dep.theme_config or {})
            current_theme.update(updates["theme_config"])
            dep.theme_config = current_theme
        if "welcome_message" in updates and updates["welcome_message"] is not None:
            dep.welcome_message = updates["welcome_message"]
        if "launcher_text" in updates and updates["launcher_text"] is not None:
            dep.launcher_text = updates["launcher_text"]

        dep.updated_at = datetime.datetime.now(datetime.UTC)
        await self.session.commit()
        return self._format_deployment(dep)

    async def get_by_public_widget_id(self, public_widget_id: str) -> AIModeDeploymentModel | None:
        """Public lookup for widget runtime initialization."""
        stmt = select(AIModeDeploymentModel).where(
            AIModeDeploymentModel.public_widget_id == public_widget_id,
            AIModeDeploymentModel.status == "ACTIVE"
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    def _format_deployment(self, d: AIModeDeploymentModel) -> dict[str, Any]:
        """Formats deployment record with generated HTML embed snippet."""
        theme = d.theme_config or {}
        primary_color = theme.get("primaryColor", "#6366f1")
        position = theme.get("position", "bottom_right")
        launcher_text = d.launcher_text or "Ask AI Mode"

        embed_code = (
            f'<!-- AI Mode Widget -->\n'
            f'<script\n'
            f'  src="https://yourstore.com/ai-mode-widget.js"\n'
            f'  data-ai-mode-widget-id="{d.public_widget_id}"\n'
            f'  data-primary-color="{primary_color}"\n'
            f'  data-position="{position}"\n'
            f'  data-launcher-text="{launcher_text}"\n'
            f'  async>\n'
            f'</script>'
        )

        return {
            "id": d.id,
            "workspace_id": d.workspace_id,
            "name": d.name,
            "public_widget_id": d.public_widget_id,
            "status": d.status,
            "allowed_domains": d.allowed_domains or ["*"],
            "theme_config": theme,
            "welcome_message": d.welcome_message,
            "launcher_text": d.launcher_text,
            "embed_code": embed_code,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None
        }
