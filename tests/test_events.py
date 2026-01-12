"""
Tests for calendar events API.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "app2gcal"


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "app2gcal"
    assert "docs" in data


@patch("app.services.calendar.calendar_service.create_event")
def test_create_event(mock_create, client):
    """Test event creation endpoint."""
    from app.schemas.event import EventResponse

    mock_create.return_value = EventResponse(
        event_id="test123",
        html_link="https://calendar.google.com/event/test123",
        summary="Test Webinar",
        start_time=datetime(2025, 2, 15, 14, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 2, 15, 15, 0, tzinfo=timezone.utc),
        status="confirmed"
    )

    response = client.post("/api/v1/events", json={
        "summary": "Test Webinar",
        "start_time": "2025-02-15T14:00:00+01:00",
        "duration_minutes": 60,
        "attendees": ["user@example.com"]
    })

    assert response.status_code == 201
    data = response.json()
    assert data["event_id"] == "test123"
    assert data["summary"] == "Test Webinar"


@patch("app.services.calendar.calendar_service.get_event")
def test_get_event(mock_get, client):
    """Test get event endpoint."""
    from app.schemas.event import EventResponse

    mock_get.return_value = EventResponse(
        event_id="test123",
        html_link="https://calendar.google.com/event/test123",
        summary="Test Webinar",
        start_time=datetime(2025, 2, 15, 14, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 2, 15, 15, 0, tzinfo=timezone.utc),
        status="confirmed"
    )

    response = client.get("/api/v1/events/test123")
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == "test123"


@patch("app.services.calendar.calendar_service.delete_event")
def test_delete_event(mock_delete, client):
    """Test delete event endpoint."""
    mock_delete.return_value = True

    response = client.delete("/api/v1/events/test123")
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] is True
    assert data["event_id"] == "test123"
