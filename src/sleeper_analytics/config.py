"""
Configuration module using pydantic-settings.

Loads settings from environment variables with sensible defaults.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="SLEEPER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Configuration
    api_title: str = "Sleeper Analytics API"
    api_version: str = "0.1.0"
    api_description: str = "Fantasy football analytics for Sleeper leagues"
    debug: bool = False

    # Sleeper API
    sleeper_base_url: str = "https://api.sleeper.app/v1"
    sleeper_timeout: float = 30.0

    # Cache Settings
    players_cache_ttl: int = 3600  # 1 hour in seconds

    # Default Season (can be overridden per request)
    default_season: int = 2024

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
