"""
Tests for POST /api/v1/bookings endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app

CONSULTANT = {
    "id": "anna-becker", "name": "Anna Becker", "role": "ERP",
    "email": "anna@test.de", "active": True, "slots": ["10:00", "14:00"]
}

VALID_BOOKING = {
    "consultants_url": "https://simplify-erp.de/c.json",
    "consultant_id": "anna-becker",
    "date": "2026-03-25",  # Wednesday
    "time": "14:00",
    "visitor": {
        "name": "Max Mustermann",
        "email": "max@firma.de",
        "company": "Musterfirma GmbH",
        "topic": "ERP rollout"
    },
    "honeypot": "",
    "context": {
        "brand": "Simplify ERP",
        "page_url": "https://simplify-erp.de/pricing",
        "page_title": "Pricing"
    }
}

ALLOWLIST = ["https://simplify-erp.de"]
API_KEY = "test-api-key-123"


@pytest.fixture
def client():
    return TestClient(app)


def _mock_settings():
    s = MagicMock()
    s.url_allowlist_prefixes = ALLOWLIST
    s.api_key = API_KEY
    s.google_calendar_id = "sales@test.de"
    s.default_calendar_id = "sales@test.de"
    s.scoopp_url = ""
    return s


# -- Honeypot --

@patch("app.routers.bookings.get_settings")
def test_honeypot_returns_fake_success(mock_settings, client):
    """Honeypot filled -> fake 200, no calendar call."""
    mock_settings.return_value = _mock_settings()
    body = {**VALID_BOOKING, "honeypot": "bot-filled-this"}
    resp = client.post("/api/v1/bookings", json=body, headers={"X-API-Key": API_KEY})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["event_id"] == ""


# -- Auth --

@patch("app.routers.bookings.get_settings")
def test_invalid_api_key(mock_settings, client):
    mock_settings.return_value = _mock_settings()
    resp = client.post("/api/v1/bookings", json=VALID_BOOKING, headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_missing_api_key(client):
    resp = client.post("/api/v1/bookings", json=VALID_BOOKING)
    assert resp.status_code == 422  # FastAPI validation error for missing header


# -- Validation --

@patch("app.routers.bookings.get_settings")
@patch("app.routers.bookings.consultant_loader.validate_url")
@patch("app.routers.bookings.consultant_loader.get_consultant_by_id", new_callable=AsyncMock)
def test_weekend_date_rejected(mock_get_c, mock_validate, mock_settings, client):
    mock_settings.return_value = _mock_settings()
    mock_get_c.return_value = CONSULTANT
    body = {**VALID_BOOKING, "date": "2026-03-28"}  # Saturday
    resp = client.post("/api/v1/bookings", json=body, headers={"X-API-Key": API_KEY})
    assert resp.status_code == 422
    assert "working day" in resp.json()["detail"]


@patch("app.routers.bookings.get_settings")
@patch("app.routers.bookings.consultant_loader.validate_url")
@patch("app.routers.bookings.consultant_loader.get_consultant_by_id", new_callable=AsyncMock)
def test_invalid_slot_rejected(mock_get_c, mock_validate, mock_settings, client):
    mock_settings.return_value = _mock_settings()
    mock_get_c.return_value = CONSULTANT
    body = {**VALID_BOOKING, "time": "11:00"}  # not in slots
    resp = client.post("/api/v1/bookings", json=body, headers={"X-API-Key": API_KEY})
    assert resp.status_code == 422
    assert "slots" in resp.json()["detail"]


@patch("app.routers.bookings.get_settings")
@patch("app.routers.bookings.consultant_loader.validate_url")
@patch("app.routers.bookings.consultant_loader.get_consultant_by_id", new_callable=AsyncMock)
def test_consultant_not_found(mock_get_c, mock_validate, mock_settings, client):
    mock_settings.return_value = _mock_settings()
    mock_get_c.return_value = None
    resp = client.post("/api/v1/bookings", json=VALID_BOOKING, headers={"X-API-Key": API_KEY})
    assert resp.status_code == 404


# -- Success --

@patch("app.routers.bookings.get_settings")
@patch("app.routers.bookings.consultant_loader.validate_url")
@patch("app.routers.bookings.consultant_loader.get_consultant_by_id", new_callable=AsyncMock)
@patch("app.routers.bookings.calendar_service")
def test_booking_success(mock_cal, mock_get_c, mock_validate, mock_settings, client):
    mock_settings.return_value = _mock_settings()
    mock_get_c.return_value = CONSULTANT
    mock_cal.create_booking_event.return_value = {
        "event_id": "gcal-evt-123",
        "html_link": "https://calendar.google.com/event/gcal-evt-123",
        "meet_link": "https://meet.google.com/abc-def-ghi",
        "status": "confirmed",
    }

    resp = client.post("/api/v1/bookings", json=VALID_BOOKING, headers={"X-API-Key": API_KEY})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["event_id"] == "gcal-evt-123"
    assert data["meet_link"] == "https://meet.google.com/abc-def-ghi"
    assert "booking_id" in data

    # Verify calendar was called with correct summary
    call_kwargs = mock_cal.create_booking_event.call_args
    assert "Anna Becker" in call_kwargs.kwargs.get("summary", "") or "Anna Becker" in str(call_kwargs)


# -- URL blocked --

@patch("app.routers.bookings.get_settings")
@patch("app.routers.bookings.consultant_loader.validate_url", side_effect=ValueError("blocked"))
def test_url_blocked(mock_validate, mock_settings, client):
    mock_settings.return_value = _mock_settings()
    resp = client.post("/api/v1/bookings", json=VALID_BOOKING, headers={"X-API-Key": API_KEY})
    assert resp.status_code == 400
