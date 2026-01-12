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
    allowed_origins: str = "http://localhost:5173,https://simplify-erp.de"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Environment
    environment: str = "dev"  # dev, stag, prod

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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
