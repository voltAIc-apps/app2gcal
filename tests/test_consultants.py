"""
Tests for GET /api/v1/consultants endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app

SAMPLE_ACTIVE = [
    {"id": "anna-becker", "name": "Anna Becker", "role": "ERP", "email": "anna@test.de", "active": True, "slots": ["10:00"]},
]

ALLOWLIST = ["https://simplify-erp.de"]


@pytest.fixture
def client():
    return TestClient(app)


@patch("app.routers.consultants.get_settings")
@patch("app.routers.consultants.consultant_loader.get_active_consultants", new_callable=AsyncMock)
@patch("app.routers.consultants.consultant_loader.validate_url")
def test_list_consultants_success(mock_validate, mock_active, mock_settings, client):
    mock_settings.return_value.url_allowlist_prefixes = ALLOWLIST
    mock_active.return_value = SAMPLE_ACTIVE

    resp = client.get("/api/v1/consultants", params={"consultants_url": "https://simplify-erp.de/c.json"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "anna-becker"
    assert data[0]["name"] == "Anna Becker"
    # Email must NOT be in response
    assert "email" not in data[0]


@patch("app.routers.consultants.get_settings")
@patch("app.routers.consultants.consultant_loader.validate_url", side_effect=ValueError("blocked"))
def test_list_consultants_url_blocked(mock_validate, mock_settings, client):
    mock_settings.return_value.url_allowlist_prefixes = ALLOWLIST
    resp = client.get("/api/v1/consultants", params={"consultants_url": "https://evil.com/c.json"})
    assert resp.status_code == 400


@patch("app.routers.consultants.get_settings")
@patch("app.routers.consultants.consultant_loader.validate_url")
@patch("app.routers.consultants.consultant_loader.get_active_consultants", new_callable=AsyncMock, side_effect=Exception("network"))
def test_list_consultants_fetch_fail(mock_active, mock_validate, mock_settings, client):
    mock_settings.return_value.url_allowlist_prefixes = ALLOWLIST
    resp = client.get("/api/v1/consultants", params={"consultants_url": "https://simplify-erp.de/c.json"})
    assert resp.status_code == 502
