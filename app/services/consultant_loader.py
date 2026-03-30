"""
Fetch, validate, and cache consultants.json from brand-hosted URLs.
SSRF prevention via URL prefix allowlist.
Schedule-to-slot expansion for weekly schedule + exceptions format.
"""
import time
import logging
from datetime import date
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


_WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def expand_schedule_slots(consultant: dict, target_date: date) -> list[str]:
    """
    Expand a consultant's weekly schedule into discrete time slots for a given date.
    Handles schedule format: {"mon": ["09:00-12:00","14:00-17:00"], ...}
    Respects exceptions: {"2026-04-10": [], "2026-04-11": ["10:00-12:00"]}
    Returns sorted list of slot start times, e.g. ["09:00","09:30","10:00",...]
    Falls back to legacy "slots" array if no schedule is present.
    """
    # Legacy flat slots array
    if "slots" in consultant and consultant["slots"]:
        return consultant["slots"]

    schedule = consultant.get("schedule", {})
    exceptions = consultant.get("exceptions", {})
    slot_duration = consultant.get("slotDuration", 30)
    date_str = target_date.isoformat()

    # Check exceptions first — overrides the weekly schedule for this date
    if date_str in exceptions:
        ranges = exceptions[date_str]
    else:
        weekday_key = _WEEKDAY_KEYS[target_date.weekday()]
        ranges = schedule.get(weekday_key, [])

    if not ranges:
        return []

    # Expand time ranges into discrete slots
    slots = []
    for time_range in ranges:
        start_str, end_str = time_range.split("-")
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        current = start_minutes
        while current + slot_duration <= end_minutes:
            h, m = divmod(current, 60)
            slots.append(f"{h:02d}:{m:02d}")
            current += slot_duration

    return sorted(slots)


def clear_cache() -> None:
    """Clear the consultant cache (for testing)."""
    _cache.clear()
