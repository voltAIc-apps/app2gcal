# app2gcal

Google Calendar Microservice - FastAPI-based REST API for managing calendar events.

## Setup

1. Copy `.env.example` to `.env`
2. Add Google service account credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `uvicorn app.main:app --reload`

## API

- `POST /api/v1/events` - Create event
- `GET /api/v1/events/{id}` - Get event
- `DELETE /api/v1/events/{id}` - Delete event
- `GET /health` - Health check

## Docker

```bash
docker build -t app2gcal .
docker run -p 8000:8000 --env-file .env app2gcal
```

## K8s

```bash
kubectl apply -f k8s/
```
