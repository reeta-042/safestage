from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "SafeStage API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = ""

    # Database (SQLite)
    DATABASE_URL: str = "sqlite:///./safestage.db"

    # Climate Provider ("mock" or "fortyguard")
    CLIMATE_PROVIDER: str = "mock"
    FORTYGUARD_API_KEY: Optional[str] = None
    FORTYGUARD_BASE_URL: str = "https://api.fortyguard.com"

    # AI Engine (Groq / OpenAI-compatible API)
    AI_API_KEY: Optional[str] = None
    AI_MODEL: str = "openai/gpt-oss-120b"
    AI_BASE_URL: str = "https://api.groq.com/openai/v1"

    # Map Provider ("fortyguard" or "osm")
    MAP_PROVIDER: str = "fortyguard"

    # Allowed frontend origins for CORS (comma-separated in env)
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Geocoding Provider ("osm" for OpenStreetMap Nominatim)
    GEOCODING_PROVIDER: str = "osm"

    # Climate cache TTL in seconds (default 1 hour)
    CLIMATE_CACHE_TTL_SECONDS: int = 3600

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

