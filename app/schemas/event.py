"""
Pydantic models for calendar events.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class EventCreate(BaseModel):
    """Request model for creating a calendar event."""

    calendar_id: Optional[str] = Field(
        default=None,
        description="Target calendar ID. Uses default if not specified."
    )
    summary: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Event title/summary"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Event description"
    )
    start_time: datetime = Field(
        ...,
        description="Event start time in ISO 8601 format"
    )
    duration_minutes: int = Field(
        ...,
        gt=0,
        le=480,
        description="Event duration in minutes (max 8 hours)"
    )
    location: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Event location or meeting link"
    )
    attendees: list[EmailStr] = Field(
        default=[],
        max_length=50,
        description="List of attendee email addresses"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "calendar_id": "ashantc@euroblaze.de",
                "summary": "CRM Deep Dive Webinar",
                "description": "Learn about Odoo CRM features",
                "start_time": "2025-02-15T14:00:00+01:00",
                "duration_minutes": 60,
                "attendees": ["user@example.com"]
            }
        }


class EventResponse(BaseModel):
    """Response model for created/retrieved event."""

    event_id: str = Field(..., description="Google Calendar event ID")
    html_link: str = Field(..., description="Link to view event in Google Calendar")
    summary: str = Field(..., description="Event title")
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    status: str = Field(default="confirmed", description="Event status")


class EventDelete(BaseModel):
    """Response model for deleted event."""

    event_id: str
    deleted: bool = True
    message: str = "Event deleted successfully"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    service: str = "app2gcal"
    version: str = "1.0.0"
