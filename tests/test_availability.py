"""
Tests for GET /api/v1/availability endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app

CONSULTANT = {
    "id": "anna-becker", "name": "Anna Becker", "role": "ERP",
    "email": "anna@test.de", "active": True, "slots": ["10:00", "14:00"]
}

ALLOWLIST = ["https://simplify-erp.de"]


@pytest.fixture
def client():
    return TestClient(app)


def _mock_settings():
    s = MagicMock()
    s.url_allowlist_prefixes = ALLOWLIST
    s.google_calendar_id = "sales@test.de"
    s.default_calendar_id = "sales@test.de"
    return s


@patch("app.routers.availability.get_settings")
@patch("app.routers.availability.calendar_service")
@patch("app.routers.availability.consultant_loader.get_consultant_by_id", new_callable=AsyncMock)
@patch("app.routers.availability.consultant_loader.validate_url")
def test_availability_all_free(mock_validate, mock_get_c, mock_cal, mock_settings, client):
    mock_settings.return_value = _mock_settings()
    mock_get_c.return_value = CONSULTANT
    mock_cal.list_events.return_value = []  # no events

    resp = client.get("/api/v1/availability", params={
        "consultants_url": "https://simplify-erp.de/c.json",
        "consultant_id": "anna-becker",
        "date_from": "2026-03-23",  # Monday
        "date_to": "2026-03-23",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["consultant_id"] == "anna-becker"
    # 1 day x 2 slots = 2 slots
    assert len(data["slots"]) == 2
    assert all(s["available"] for s in data["slots"])


@patch("app.routers.availability.get_settings")
@patch("app.routers.availability.calendar_service")
@patch("app.routers.availability.consultant_loader.get_consultant_by_id", new_callable=AsyncMock)
@patch("app.routers.availability.consultant_loader.validate_url")
def test_availability_slot_taken(mock_validate, mock_get_c, mock_cal, mock_settings, client):
    """Slot at 10:00 with Anna Becker in title should be unavailable."""
    mock_settings.return_value = _mock_settings()
    mock_get_c.return_value = CONSULTANT
    mock_cal.list_events.return_value = [
        {
            "summary": "Meeting with Anna Becker",
            "description": "",
            "start": {"dateTime": "2026-03-23T10:00:00+01:00"},
        }
    ]

    resp = client.get("/api/v1/availability", params={
        "consultants_url": "https://simplify-erp.de/c.json",
        "consultant_id": "anna-becker",
        "date_from": "2026-03-23",
        "date_to": "2026-03-23",
    })
    assert resp.status_code == 200
    slots = resp.json()["slots"]
    slot_10 = next(s for s in slots if s["time"] == "10:00")
    slot_14 = next(s for s in slots if s["time"] == "14:00")
    assert slot_10["available"] is False
    assert slot_14["available"] is True


@patch("app.routers.availability.get_settings")
@patch("app.routers.availability.consultant_loader.validate_url")
@patch("app.routers.availability.consultant_loader.get_consultant_by_id", new_callable=AsyncMock)
def test_availability_consultant_not_found(mock_get_c, mock_validate, mock_settings, client):
    mock_settings.return_value = _mock_settings()
    mock_get_c.return_value = None

    resp = client.get("/api/v1/availability", params={
        "consultants_url": "https://simplify-erp.de/c.json",
        "consultant_id": "nobody",
        "date_from": "2026-03-23",
    })
    assert resp.status_code == 404


@patch("app.routers.availability.get_settings")
@patch("app.routers.availability.consultant_loader.validate_url", side_effect=ValueError("blocked"))
def test_availability_url_blocked(mock_validate, mock_settings, client):
    mock_settings.return_value = _mock_settings()
    resp = client.get("/api/v1/availability", params={
        "consultants_url": "https://evil.com/c.json",
        "consultant_id": "anna-becker",
    })
    assert resp.status_code == 400


@patch("app.routers.availability.get_settings")
@patch("app.routers.availability.calendar_service")
@patch("app.routers.availability.consultant_loader.get_consultant_by_id", new_callable=AsyncMock)
@patch("app.routers.availability.consultant_loader.validate_url")
def test_availability_skips_weekends(mock_validate, mock_get_c, mock_cal, mock_settings, client):
    """Weekend days should not appear in slots."""
    mock_settings.return_value = _mock_settings()
    mock_get_c.return_value = CONSULTANT
    mock_cal.list_events.return_value = []

    resp = client.get("/api/v1/availability", params={
        "consultants_url": "https://simplify-erp.de/c.json",
        "consultant_id": "anna-becker",
        "date_from": "2026-03-28",  # Saturday
        "date_to": "2026-03-29",    # Sunday
    })
    assert resp.status_code == 200
    assert len(resp.json()["slots"]) == 0


@patch("app.routers.availability.get_settings")
@patch("app.routers.availability.consultant_loader.validate_url")
@patch("app.routers.availability.consultant_loader.get_consultant_by_id", new_callable=AsyncMock)
def test_availability_date_from_after_date_to(mock_get_c, mock_validate, mock_settings, client):
    """date_from > date_to should return 422."""
    mock_settings.return_value = _mock_settings()
    mock_get_c.return_value = CONSULTANT

    resp = client.get("/api/v1/availability", params={
        "consultants_url": "https://simplify-erp.de/c.json",
        "consultant_id": "anna-becker",
        "date_from": "2026-03-30",
        "date_to": "2026-03-23",
    })
    assert resp.status_code == 422
    assert "date_from" in resp.json()["detail"]
