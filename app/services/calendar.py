"""
Google Calendar API service wrapper.
"""
from datetime import datetime, timedelta
from typing import Optional
import logging

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import get_settings
from app.schemas.event import EventCreate, EventResponse

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    """Service for interacting with Google Calendar API."""

    def __init__(self):
        self.settings = get_settings()
        self._service = None

    @property
    def service(self):
        """Lazy-load Google Calendar service."""
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self):
        """Build authenticated Google Calendar service."""
        credentials = Credentials.from_service_account_info(
            self.settings.google_credentials,
            scopes=SCOPES
        )
        return build("calendar", "v3", credentials=credentials)

    def create_event(self, event_data: EventCreate) -> EventResponse:
        """
        Create a new calendar event.

        Args:
            event_data: Event creation data

        Returns:
            EventResponse with created event details
        """
        calendar_id = event_data.calendar_id or self.settings.default_calendar_id

        # Calculate end time
        start_dt = event_data.start_time
        end_dt = start_dt + timedelta(minutes=event_data.duration_minutes)

        # Build event body
        event_body = {
            "summary": event_data.summary,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Europe/Berlin",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Europe/Berlin",
            },
        }

        if event_data.description:
            event_body["description"] = event_data.description

        if event_data.location:
            event_body["location"] = event_data.location

        if event_data.attendees:
            event_body["attendees"] = [
                {"email": email} for email in event_data.attendees
            ]
            # Send email notifications to attendees
            event_body["sendUpdates"] = "all"

        try:
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_body,
                sendUpdates="all" if event_data.attendees else "none"
            ).execute()

            logger.info(f"Created event: {created_event['id']}")

            return EventResponse(
                event_id=created_event["id"],
                html_link=created_event["htmlLink"],
                summary=created_event["summary"],
                start_time=datetime.fromisoformat(
                    created_event["start"]["dateTime"].replace("Z", "+00:00")
                ),
                end_time=datetime.fromisoformat(
                    created_event["end"]["dateTime"].replace("Z", "+00:00")
                ),
                status=created_event.get("status", "confirmed")
            )

        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            raise

    def get_event(
        self,
        event_id: str,
        calendar_id: Optional[str] = None
    ) -> EventResponse:
        """
        Get an event by ID.

        Args:
            event_id: Google Calendar event ID
            calendar_id: Optional calendar ID

        Returns:
            EventResponse with event details
        """
        cal_id = calendar_id or self.settings.default_calendar_id

        try:
            event = self.service.events().get(
                calendarId=cal_id,
                eventId=event_id
            ).execute()

            return EventResponse(
                event_id=event["id"],
                html_link=event["htmlLink"],
                summary=event["summary"],
                start_time=datetime.fromisoformat(
                    event["start"]["dateTime"].replace("Z", "+00:00")
                ),
                end_time=datetime.fromisoformat(
                    event["end"]["dateTime"].replace("Z", "+00:00")
                ),
                status=event.get("status", "confirmed")
            )

        except HttpError as e:
            logger.error(f"Failed to get event {event_id}: {e}")
            raise

    def delete_event(
        self,
        event_id: str,
        calendar_id: Optional[str] = None
    ) -> bool:
        """
        Delete an event by ID.

        Args:
            event_id: Google Calendar event ID
            calendar_id: Optional calendar ID

        Returns:
            True if deleted successfully
        """
        cal_id = calendar_id or self.settings.default_calendar_id

        try:
            self.service.events().delete(
                calendarId=cal_id,
                eventId=event_id,
                sendUpdates="all"
            ).execute()

            logger.info(f"Deleted event: {event_id}")
            return True

        except HttpError as e:
            logger.error(f"Failed to delete event {event_id}: {e}")
            raise


# Singleton instance
calendar_service = CalendarService()
