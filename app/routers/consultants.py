"""
GET /api/v1/consultants — active consultant list for booking widget.
"""
import logging
from fastapi import APIRouter, Query, HTTPException
import httpx

from app.config import get_settings
from app.models.booking import ConsultantPublic
from app.services import consultant_loader

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/consultants", tags=["consultants"])


@router.get("", response_model=list[ConsultantPublic])
async def list_consultants(
    consultants_url: str = Query(..., description="URL of the brand's consultants.json")
):
    """Return active consultants. Email is never exposed."""
    settings = get_settings()

    # SSRF check
    try:
        consultant_loader.validate_url(consultants_url, settings.url_allowlist_prefixes)
    except ValueError:
        raise HTTPException(status_code=400, detail="consultants_url not on allowlist")

    # Fetch
    try:
        active = await consultant_loader.get_active_consultants(consultants_url)
    except (httpx.HTTPError, Exception) as e:
        logger.error(f"Failed to fetch consultants from {consultants_url}: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch consultants")

    return [
        ConsultantPublic(id=c["id"], name=c["name"], role=c.get("role", ""))
        for c in active
    ]
