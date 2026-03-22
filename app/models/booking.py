"""
Pydantic models for consultant, availability and booking endpoints.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr


# -- Consultant models --

class ConsultantFull(BaseModel):
    """Internal consultant record from consultants.json."""
    id: str
    name: str
    role: str = ""
    email: str
    active: bool = True
    slots: list[str] = []


class ConsultantPublic(BaseModel):
    """Public consultant response — no email, no slots."""
    id: str
    name: str
    role: str = ""


# -- Availability models --

class AvailabilitySlot(BaseModel):
    date: str
    time: str
    available: bool


class AvailabilityResponse(BaseModel):
    consultant_id: str
    slots: list[AvailabilitySlot]


# -- Booking models --

class VisitorInfo(BaseModel):
    name: str
    email: EmailStr
    company: str
    topic: str = ""


class BookingContext(BaseModel):
    """Lead context passed through from the booking widget."""
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    lang: Optional[str] = None
    timestamp: Optional[str] = None
    brand: Optional[str] = None
    custom: Optional[dict] = None


class BookingRequest(BaseModel):
    consultants_url: str
    consultant_id: str
    date: str
    time: str
    visitor: VisitorInfo
    additional_attendees: list[EmailStr] = []
    honeypot: str = ""
    context: Optional[BookingContext] = None


class BookingResponse(BaseModel):
    booking_id: str
    event_id: str = ""
    status: str = "confirmed"
    meet_link: str = ""
