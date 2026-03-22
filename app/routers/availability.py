"""
GET /api/v1/availability — free/busy slots for a consultant on a date range.
"""
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, HTTPException
import httpx

from app.config import get_settings
from app.models.booking import AvailabilitySlot, AvailabilityResponse
from app.services import consultant_loader
from app.services.calendar import calendar_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/availability", tags=["availability"])

TZ_BERLIN = ZoneInfo("Europe/Berlin")


@router.get("", response_model=AvailabilityResponse)
async def get_availability(
    consultants_url: str = Query(..., description="URL of the brand's consultants.json"),
    consultant_id: str = Query(...),
    date_from: date = Query(None, description="ISO date (default: today)"),
    date_to: date = Query(None, description="ISO date (default: date_from + 14 days)"),
):
    settings = get_settings()

    # SSRF check
    try:
        consultant_loader.validate_url(consultants_url, settings.url_allowlist_prefixes)
    except ValueError:
        raise HTTPException(status_code=400, detail="consultants_url not on allowlist")

    # Fetch consultant
    try:
        consultant = await consultant_loader.get_consultant_by_id(consultants_url, consultant_id)
    except (httpx.HTTPError, Exception) as e:
        logger.error(f"Failed to fetch consultants: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch consultants")

    if not consultant or not consultant.get("active", True):
        raise HTTPException(status_code=404, detail="Consultant not found or inactive")

    # Date range defaults
    if date_from is None:
        date_from = date.today()
    if date_to is None:
        date_to = date_from + timedelta(days=14)

    # Fetch calendar events for the range
    time_min = datetime(date_from.year, date_from.month, date_from.day, 0, 0, tzinfo=TZ_BERLIN)
    time_max = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=TZ_BERLIN)

    calendar_id = settings.google_calendar_id or settings.default_calendar_id
    try:
        events = calendar_service.list_events(calendar_id, time_min, time_max)
    except Exception as e:
        logger.error(f"Calendar list_events failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to query calendar")

    # Build slot availability
    consultant_name = consultant["name"].lower()
    slot_times = consultant.get("slots", [])
    slots: list[AvailabilitySlot] = []

    current = date_from
    while current <= date_to:
        # Only working days (Mon=0 .. Fri=4)
        if current.weekday() < 5:
            for slot_time in slot_times:
                # Check if any event at this slot mentions the consultant
                available = True
                for ev in events:
                    ev_start = ev.get("start", {}).get("dateTime", "")
                    if not ev_start:
                        continue
                    # Parse event start and compare date + time
                    try:
                        ev_dt = datetime.fromisoformat(ev_start.replace("Z", "+00:00"))
                        ev_date_str = ev_dt.astimezone(TZ_BERLIN).strftime("%Y-%m-%d")
                        ev_time_str = ev_dt.astimezone(TZ_BERLIN).strftime("%H:%M")
                    except (ValueError, TypeError):
                        continue

                    if ev_date_str == current.isoformat() and ev_time_str == slot_time:
                        # Check if consultant name in title or description
                        summary = (ev.get("summary") or "").lower()
                        description = (ev.get("description") or "").lower()
                        if consultant_name in summary or consultant_name in description:
                            available = False
                            break

                slots.append(AvailabilitySlot(
                    date=current.isoformat(),
                    time=slot_time,
                    available=available
                ))
        current += timedelta(days=1)

    return AvailabilityResponse(consultant_id=consultant_id, slots=slots)
