"""
POST /api/v1/bookings — create booking end-to-end.
Validates, writes calendar event with Meet, fires async scoopp research.
"""
import hmac
import logging
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
import httpx

from app.config import get_settings
from app.models.booking import BookingRequest, BookingResponse
from app.services import consultant_loader
from app.services.calendar import calendar_service
from app.services import scoopp_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])

TZ_BERLIN = ZoneInfo("Europe/Berlin")
WEEKDAY_NAMES = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def _verify_api_key(x_api_key: str) -> None:
    """Compare API key against settings. Raises 401 on mismatch."""
    settings = get_settings()
    if not settings.api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("", response_model=BookingResponse)
async def create_booking(
    req: BookingRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(...),
):
    settings = get_settings()

    # 1. Honeypot — silent fake success
    if req.honeypot:
        logger.info("Honeypot triggered, discarding booking")
        return BookingResponse(
            booking_id=str(uuid.uuid4()),
            status="confirmed",
            meet_link=""
        )

    # 2. API key auth
    _verify_api_key(x_api_key)

    # 3. Validate consultants_url
    try:
        consultant_loader.validate_url(req.consultants_url, settings.url_allowlist_prefixes)
    except ValueError:
        raise HTTPException(status_code=400, detail="consultants_url not on allowlist")

    # 4. Fetch consultant
    try:
        consultant = await consultant_loader.get_consultant_by_id(
            req.consultants_url, req.consultant_id
        )
    except (httpx.HTTPError, Exception) as e:
        logger.error(f"Failed to fetch consultants: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch consultants")

    if not consultant or not consultant.get("active", True):
        raise HTTPException(status_code=404, detail="Consultant not found or inactive")

    # 5. Validate date is Mon-Fri
    try:
        booking_date = date.fromisoformat(req.date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format")

    if booking_date.weekday() >= 5:
        raise HTTPException(status_code=422, detail="Date must be a working day (Mon-Fri)")

    # 6. Validate time is in consultant's slots
    if req.time not in consultant.get("slots", []):
        raise HTTPException(status_code=422, detail="Time not in consultant's available slots")

    # 7. Build calendar event
    brand = (req.context.brand if req.context and req.context.brand else "Booking")
    consultant_name = consultant["name"]
    consultant_email = consultant["email"]

    # Title per spec
    summary = f"[{brand}] {req.visitor.name} ({req.visitor.company}) \u2194 {consultant_name}"

    # Parse start datetime
    hour, minute = map(int, req.time.split(":"))
    start_dt = datetime(
        booking_date.year, booking_date.month, booking_date.day,
        hour, minute, tzinfo=TZ_BERLIN
    )
    end_dt = start_dt + timedelta(minutes=30)

    weekday_name = WEEKDAY_NAMES[booking_date.weekday()]
    end_time_str = end_dt.strftime("%H:%M")
    formatted_date = booking_date.strftime("%d %B %Y")

    # Description per spec
    desc_lines = [
        "Booked via website",
        "",
        f"Visitor:     {req.visitor.name}",
        f"Company:     {req.visitor.company}",
        f"Email:       {req.visitor.email}",
    ]
    if req.visitor.topic:
        desc_lines.append(f"Topic:       {req.visitor.topic}")
    desc_lines += [
        "",
        f"Consultant:  {consultant_name} ({consultant_email})",
        f"Scheduled:   {weekday_name}, {formatted_date} \u00b7 {req.time}\u2013{end_time_str} CET",
    ]

    # Lead context section
    if req.context:
        ctx = req.context
        has_context = any([ctx.page_title, ctx.page_url, ctx.utm_source, ctx.custom])
        if has_context:
            desc_lines += ["", "--- Lead context ---"]
            if ctx.page_title:
                desc_lines.append(f"Page:        {ctx.page_title}")
            if ctx.page_url:
                desc_lines.append(f"URL:         {ctx.page_url}")
            # Source line: utm_source / utm_medium / utm_campaign
            source_parts = [p for p in [ctx.utm_source, ctx.utm_medium, ctx.utm_campaign] if p]
            if source_parts:
                desc_lines.append(f"Source:      {' / '.join(source_parts)}")
            if ctx.custom:
                for key, val in ctx.custom.items():
                    desc_lines.append(f"{key.capitalize()}:{'  ' * max(1, 5 - len(key) // 4)}{val}")

    description = "\n".join(desc_lines)

    # Attendees — deduplicate while preserving order
    calendar_id = settings.google_calendar_id or settings.default_calendar_id
    seen = set()
    attendees = []
    for email in [calendar_id, consultant_email, req.visitor.email] + [str(a) for a in req.additional_attendees]:
        if email not in seen:
            seen.add(email)
            attendees.append(email)

    # 8. Create calendar event with Meet
    try:
        result = calendar_service.create_booking_event(
            calendar_id=calendar_id,
            summary=summary,
            description=description,
            start_dt=start_dt,
            attendees=attendees,
        )
    except Exception as e:
        logger.error(f"Calendar event creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create calendar event")

    booking_id = str(uuid.uuid4())
    meet_link = result.get("meet_link", "")

    # 9. Async scoopp research (BackgroundTasks)
    if settings.scoopp_url:
        scoopp_payload = {
            "company_name": req.visitor.company,
            "person_name": req.visitor.name,
            "person_email": req.visitor.email,
            "format": "brief",
            "mail_to": consultant_email,
            "mail_subject": (
                f"New booking: {req.visitor.name} ({req.visitor.company}) "
                f"\u00b7 {weekday_name} {req.date} {req.time}"
            ),
            "mail_context": {
                "consultant_name": consultant_name,
                "meeting_date": formatted_date,
                "meeting_time": f"{req.time}\u2013{end_time_str} CET",
                "topic": req.visitor.topic,
                "meet_link": meet_link,
            },
        }
        # Pass context verbatim if present
        if req.context:
            scoopp_payload["context"] = req.context.model_dump(exclude_none=True)

        background_tasks.add_task(
            scoopp_client.dispatch_research, settings.scoopp_url, scoopp_payload
        )

    return BookingResponse(
        booking_id=booking_id,
        event_id=result["event_id"],
        status="confirmed",
        meet_link=meet_link,
    )
