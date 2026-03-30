"""
Configuration settings loaded from environment variables.
"""
import os
import json
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment."""

    # Google Calendar API credentials (JSON string)
    google_credentials_json: str = ""

    # Default calendar ID for events
    default_calendar_id: str = "ashantc@euroblaze.de"

    # CORS allowed origins (comma-separated)
    allowed_origins: str = "http://localhost:5173,http://10.0.99.1:5180,https://simplify-erp.de,https://www.simplify-erp.de"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Environment
    environment: str = "dev"  # dev, stag, prod

    # Booking calendar ID (e.g. sales@simplify-erp.de)
    google_calendar_id: str = ""

    # Scoopp research service URL
    scoopp_url: str = ""

    # API key for authenticated endpoints (X-API-Key header)
    api_key: str = ""

    # SSRF allowlist for consultants_url (comma-separated URL prefixes)
    consultants_url_allowlist: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def google_credentials(self) -> dict:
        """Parse Google credentials JSON string."""
        if not self.google_credentials_json:
            return {}
        return json.loads(self.google_credentials_json)

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def url_allowlist_prefixes(self) -> list[str]:
        """Parse consultants URL allowlist from comma-separated prefixes."""
        if not self.consultants_url_allowlist:
            return []
        return [p.strip() for p in self.consultants_url_allowlist.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
