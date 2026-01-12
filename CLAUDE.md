# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

app2gcal is a FastAPI microservice for managing Google Calendar events. Designed as a standalone k8s-deployable service that other applications can call via REST API.

## Commands

```bash
# Development
pip install -r requirements.txt
uvicorn app.main:app --reload

# Run tests
pytest tests/

# Run single test
pytest tests/test_events.py::test_create_event -v

# Docker
docker build -t app2gcal .
docker run -p 8000:8000 --env-file .env app2gcal

# Kubernetes
kubectl apply -f k8s/
```

## Architecture

```
app/
  main.py          # FastAPI app, lifespan, CORS, routes
  config.py        # pydantic-settings, env loading, get_settings()
  routers/
    events.py      # /api/v1/events endpoints (POST, GET, DELETE)
  services/
    calendar.py    # CalendarService - Google Calendar API wrapper (singleton)
  schemas/
    event.py       # Pydantic models: EventCreate, EventResponse, EventDelete
```

**Flow**: Request -> Router (events.py) -> Service (calendar.py) -> Google Calendar API

**Key patterns**:
- `get_settings()` returns cached Settings instance (lru_cache)
- `calendar_service` is a module-level singleton in services/calendar.py
- Google credentials loaded from `GOOGLE_CREDENTIALS_JSON` env var (JSON string)
- Default timezone: Europe/Berlin

## Configuration

Environment variables (see .env.example):
- `GOOGLE_CREDENTIALS_JSON` - Service account JSON (required for prod)
- `DEFAULT_CALENDAR_ID` - Target calendar email
- `ALLOWED_ORIGINS` - CORS origins, comma-separated
- `ENVIRONMENT` - dev/stag/prod

## API Endpoints

- `POST /api/v1/events` - Create event (returns 201)
- `GET /api/v1/events/{id}` - Get event
- `DELETE /api/v1/events/{id}` - Delete event
- `GET /health` - Health check for k8s probes

## Testing

Tests use mocked `calendar_service` methods (patch decorator). No real Google API calls in tests.
