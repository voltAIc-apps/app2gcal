"""
Tests for consultant_loader service — URL validation, fetching, caching.
"""
import pytest
import time
from unittest.mock import patch, AsyncMock, MagicMock

from app.services import consultant_loader


SAMPLE_CONSULTANTS = [
    {"id": "anna-becker", "name": "Anna Becker", "role": "ERP", "email": "anna@test.de", "active": True, "slots": ["10:00", "14:00"]},
    {"id": "tobias-kern", "name": "Tobias Kern", "role": "Automation", "email": "tobias@test.de", "active": False, "slots": ["09:00"]},
]

ALLOWLIST = ["https://simplify-erp.de", "http://frontend-service"]


def setup_function():
    """Clear cache before each test."""
    consultant_loader.clear_cache()


# -- URL validation --

def test_validate_url_allowed():
    consultant_loader.validate_url("https://simplify-erp.de/data/consultants.json", ALLOWLIST)


def test_validate_url_blocked():
    with pytest.raises(ValueError, match="not on allowlist"):
        consultant_loader.validate_url("https://evil.com/steal", ALLOWLIST)


def test_validate_url_empty_allowlist():
    with pytest.raises(ValueError):
        consultant_loader.validate_url("https://simplify-erp.de/data/consultants.json", [])


# -- Fetching --

@pytest.mark.asyncio
@patch("app.services.consultant_loader.httpx.AsyncClient")
async def test_fetch_consultants(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_CONSULTANTS
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    result = await consultant_loader.fetch_consultants("https://simplify-erp.de/consultants.json")
    assert len(result) == 2
    assert result[0]["id"] == "anna-becker"


@pytest.mark.asyncio
@patch("app.services.consultant_loader.httpx.AsyncClient")
async def test_fetch_uses_cache(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_CONSULTANTS
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    url = "https://simplify-erp.de/cached.json"
    await consultant_loader.fetch_consultants(url)
    await consultant_loader.fetch_consultants(url)
    # Only one HTTP call despite two fetches
    assert mock_client.get.call_count == 1


# -- Filtering --

@pytest.mark.asyncio
@patch("app.services.consultant_loader.fetch_consultants", new_callable=AsyncMock)
async def test_get_active_consultants(mock_fetch):
    mock_fetch.return_value = SAMPLE_CONSULTANTS
    result = await consultant_loader.get_active_consultants("https://test.de/c.json")
    assert len(result) == 1
    assert result[0]["id"] == "anna-becker"


@pytest.mark.asyncio
@patch("app.services.consultant_loader.fetch_consultants", new_callable=AsyncMock)
async def test_get_consultant_by_id_found(mock_fetch):
    mock_fetch.return_value = SAMPLE_CONSULTANTS
    result = await consultant_loader.get_consultant_by_id("https://test.de/c.json", "tobias-kern")
    assert result["name"] == "Tobias Kern"


@pytest.mark.asyncio
@patch("app.services.consultant_loader.fetch_consultants", new_callable=AsyncMock)
async def test_get_consultant_by_id_not_found(mock_fetch):
    mock_fetch.return_value = SAMPLE_CONSULTANTS
    result = await consultant_loader.get_consultant_by_id("https://test.de/c.json", "nobody")
    assert result is None
