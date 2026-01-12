"""
Calendar events API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from googleapiclient.errors import HttpError

from app.schemas.event import (
    EventCreate,
    EventResponse,
    EventDelete
)
from app.services.calendar import calendar_service

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(event_data: EventCreate) -> EventResponse:
    """
    Create a new calendar event.

    - **calendar_id**: Target calendar (defaults to configured calendar)
    - **summary**: Event title
    - **description**: Event description (optional)
    - **start_time**: Event start time (ISO 8601)
    - **duration_minutes**: Duration in minutes
    - **attendees**: List of attendee emails (optional)
    """
    try:
        return calendar_service.create_event(event_data)
    except HttpError as e:
        if e.resp.status == 404:
            raise HTTPException(status_code=404, detail="Calendar not found")
        elif e.resp.status == 403:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions for calendar"
            )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    calendar_id: Optional[str] = Query(
        default=None,
        description="Calendar ID (uses default if not specified)"
    )
) -> EventResponse:
    """
    Get a calendar event by ID.

    - **event_id**: Google Calendar event ID
    - **calendar_id**: Optional calendar ID
    """
    try:
        return calendar_service.get_event(event_id, calendar_id)
    except HttpError as e:
        if e.resp.status == 404:
            raise HTTPException(status_code=404, detail="Event not found")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{event_id}", response_model=EventDelete)
async def delete_event(
    event_id: str,
    calendar_id: Optional[str] = Query(
        default=None,
        description="Calendar ID (uses default if not specified)"
    )
) -> EventDelete:
    """
    Delete a calendar event.

    - **event_id**: Google Calendar event ID
    - **calendar_id**: Optional calendar ID
    """
    try:
        calendar_service.delete_event(event_id, calendar_id)
        return EventDelete(event_id=event_id)
    except HttpError as e:
        if e.resp.status == 404:
            raise HTTPException(status_code=404, detail="Event not found")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
