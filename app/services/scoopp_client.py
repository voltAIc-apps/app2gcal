"""
Async HTTP client for scoopp /research endpoint.
Fires after booking response is sent (BackgroundTasks).
"""
import logging
import httpx

logger = logging.getLogger(__name__)


async def dispatch_research(scoopp_url: str, payload: dict) -> None:
    """
    POST research request to scoopp.
    5s timeout — fails silently (booking is already confirmed).
    """
    url = f"{scoopp_url.rstrip('/')}/research"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info(f"Scoopp research dispatched: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Scoopp research call failed (non-blocking): {e}")
