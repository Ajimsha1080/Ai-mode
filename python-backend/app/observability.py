import json
import logging
import re
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ---------------------------------------------------------------------------
# PII REDACTION ENGINE
# ---------------------------------------------------------------------------

EMAIL_REGEX = re.compile(r'\b([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b')
PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
CARD_REGEX = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
JWT_REGEX = re.compile(r'eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}')
AUTH_HEADER_REGEX = re.compile(r'(Bearer\s+)[a-zA-Z0-9_.\-]+', re.IGNORECASE)

def mask_email(match: re.Match) -> str:
    first_char = match.group(1)
    domain = match.group(2)
    return f"{first_char}***@{domain}"

def redact_pii(data: Any) -> Any:
    """
    Recursively scans and redacts PII (Emails, Phones, Credit Cards, JWTs, Auth Secrets)
    from strings, dicts, and lists before logging or tracing.
    """
    if isinstance(data, str):
        s = data
        s = EMAIL_REGEX.sub(mask_email, s)
        s = PHONE_REGEX.sub("***-***-****", s)
        s = CARD_REGEX.sub("****-****-****-****", s)
        s = JWT_REGEX.sub("[REDACTED_JWT]", s)
        s = AUTH_HEADER_REGEX.sub(r"\1[REDACTED_TOKEN]", s)
        return s
    elif isinstance(data, dict):
        redacted = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(secret_term in k_lower for secret_term in ["password", "secret", "token", "key", "authorization", "cookie"]):
                redacted[k] = "[REDACTED_VALUE]"
            else:
                redacted[k] = redact_pii(v)
        return redacted
    elif isinstance(data, list):
        return [redact_pii(item) for item in data]
    return data


# ---------------------------------------------------------------------------
# STRUCTURED JSON LOGGER
# ---------------------------------------------------------------------------

class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON with trace and request correlation."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_pii(record.getMessage()),
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "trace_id"):
            log_obj["trace_id"] = record.trace_id
        if hasattr(record, "workspace_id"):
            log_obj["workspace_id"] = record.workspace_id
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code
        if hasattr(record, "method"):
            log_obj["method"] = record.method
        if hasattr(record, "path"):
            log_obj["path"] = record.path
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

logger = logging.getLogger("shopmate_api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    logger.addHandler(handler)


# ---------------------------------------------------------------------------
# OPENTELEMETRY / TRACE CONTEXT
# ---------------------------------------------------------------------------

class TraceContext:
    def __init__(self, trace_id: str | None = None, span_id: str | None = None):
        self.trace_id = trace_id or uuid.uuid4().hex
        self.span_id = span_id or uuid.uuid4().hex[:16]

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> "TraceContext":
        # W3C traceparent support: version-trace_id-parent_id-flags
        traceparent = headers.get("traceparent") or headers.get("x-trace-id")
        if traceparent and traceparent.startswith("00-"):
            parts = traceparent.split("-")
            if len(parts) >= 3:
                return cls(trace_id=parts[1], span_id=parts[2])
        elif traceparent:
            return cls(trace_id=traceparent)
        return cls()


# ---------------------------------------------------------------------------
# OBSERVABILITY & LOGGING MIDDLEWARE
# ---------------------------------------------------------------------------

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-Id") or f"req_{uuid.uuid4().hex[:12]}"
        trace_ctx = TraceContext.from_headers(dict(request.headers))

        request.state.request_id = req_id
        request.state.trace_id = trace_ctx.trace_id

        start_time = time.time()
        response: Response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        response.headers["X-Request-Id"] = req_id
        response.headers["X-Trace-Id"] = trace_ctx.trace_id

        # Redacted path and query parameters
        clean_path = redact_pii(request.url.path)
        workspace_id = request.headers.get("X-Workspace-Id", "unknown")

        extra = {
            "request_id": req_id,
            "trace_id": trace_ctx.trace_id,
            "workspace_id": workspace_id,
            "method": request.method,
            "path": clean_path,
            "status_code": response.status_code,
            "duration_ms": duration_ms
        }

        # Don't clutter logs with high-frequency health probes
        if clean_path not in ("/health", "/healthz", "/ready", "/readyz"):
            logger.info(
                f"{request.method} {clean_path} -> {response.status_code} ({duration_ms}ms)",
                extra=extra
            )

        return response
