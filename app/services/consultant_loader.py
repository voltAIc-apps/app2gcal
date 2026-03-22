"""
Fetch, validate, and cache consultants.json from brand-hosted URLs.
SSRF prevention via URL prefix allowlist.
"""
import time
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# In-memory cache: {url: {"data": list, "ts": float}}
_cache: dict = {}
_CACHE_TTL = 60  # seconds


def validate_url(url: str, allowlist_prefixes: list[str]) -> None:
    """Raise ValueError if url does not start with any allowed prefix."""
    for prefix in allowlist_prefixes:
        if url.startswith(prefix):
            return
    raise ValueError(f"URL not on allowlist: {url}")


async def fetch_consultants(url: str) -> list[dict]:
    """
    Fetch consultants.json from url with 60s TTL cache.
    Returns parsed list of consultant dicts.
    Raises httpx.HTTPError on fetch failure.
    """
    now = time.time()
    cached = _cache.get(url)
    if cached and (now - cached["ts"]) < _CACHE_TTL:
        return cached["data"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    _cache[url] = {"data": data, "ts": now}
    logger.info(f"Fetched consultants from {url} ({len(data)} entries)")
    return data


async def get_active_consultants(url: str) -> list[dict]:
    """Return only active consultants."""
    all_consultants = await fetch_consultants(url)
    return [c for c in all_consultants if c.get("active", True)]


async def get_consultant_by_id(url: str, consultant_id: str) -> Optional[dict]:
    """Find consultant by id. Returns None if not found."""
    all_consultants = await fetch_consultants(url)
    for c in all_consultants:
        if c.get("id") == consultant_id:
            return c
    return None


def clear_cache() -> None:
    """Clear the consultant cache (for testing)."""
    _cache.clear()
