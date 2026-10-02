import ipaddress
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger("ai_mode_crawler_adapter")

# SSRF Protection Blocklist
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # AWS/GCP Cloud Metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

def is_safe_url(url: str) -> bool:
    """Validates URL to protect against SSRF and internal network probing."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "metadata.google.internal", "169.254.169.254"):
            return False
        # Try resolving host IP
        try:
            ip = ipaddress.ip_address(hostname)
            for blocked in BLOCKED_IP_RANGES:
                if ip in blocked:
                    return False
        except ValueError:
            pass  # Hostname is not a raw IP
        return True
    except Exception:
        return False

class CrawlerAdapter:
    """
    Safe Web Crawler Adapter for AI Mode Knowledge ingestion.
    Extracts text, metadata, page title, and structured content from merchant store pages.
    """

    @classmethod
    def fetch_and_extract_url(cls, url: str) -> dict[str, Any]:
        """Fetches public webpage with strict SSRF checks, timeout, and HTML text extraction."""
        if not is_safe_url(url):
            raise ValueError(f"URL '{url}' is invalid or blocked for security reasons.")

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ShopMate-AIMode-Crawler/2.0 (+https://shopmate.ai/bot)",
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_bytes = resp.read(1024 * 1024)  # 1MB limit for safety
                html_text = raw_bytes.decode("utf-8", errors="ignore")

                # Extract Title
                title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
                title = title_match.group(1).strip() if title_match else url

                # Strip script and style tags
                cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
                # Convert common breaks to newlines
                cleaned = re.sub(r"<(br|p|div|li|h1|h2|h3|h4|h5|h6)[^>]*>", "\n", cleaned, flags=re.IGNORECASE)
                # Strip all other HTML tags
                cleaned = re.sub(r"<[^>]+>", " ", cleaned)
                # Normalize whitespace
                lines = [re.sub(r"\s+", " ", line).strip() for line in cleaned.split("\n")]
                clean_text = "\n".join(line_item for line_item in lines if line_item and len(line_item) > 10)

                paragraphs = [p for p in clean_text.split("\n") if len(p.strip()) > 30]

                return {
                    "url": url,
                    "title": title,
                    "text": clean_text[:50000],  # 50k chars max
                    "paragraphs": paragraphs[:50],
                    "status_code": resp.status
                }
        except Exception as e:
            logger.error(f"CrawlerAdapter failed to fetch {url}: {e}")
            raise RuntimeError(f"Failed to crawl {url}: {str(e)}") from e
