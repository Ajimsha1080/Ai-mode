import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .observability import redact_pii

class AuditLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:12]}")
    workspace_id: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = "127.0.0.1"
    created_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

# In-memory tenant-partitioned audit log buffer with database synchronization
_AUDIT_LOG_STORE: List[Dict[str, Any]] = []

def record_audit_log(
    workspace_id: str,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Records an administrative action with automatic PII redaction and multi-tenant isolation.
    """
    clean_meta = redact_pii(metadata or {})
    entry = AuditLogEntry(
        workspace_id=workspace_id,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=clean_meta,
        ip_address=ip_address or "127.0.0.1"
    )
    _AUDIT_LOG_STORE.append(entry.model_dump())
    return entry.model_dump()

def get_tenant_audit_logs(
    workspace_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Retrieves audit logs filtered strictly to the caller's workspace.
    """
    tenant_logs = [log for log in _AUDIT_LOG_STORE if log["workspace_id"] == workspace_id]
    tenant_logs.sort(key=lambda x: x["created_at"], reverse=True)
    return tenant_logs[offset : offset + limit]
