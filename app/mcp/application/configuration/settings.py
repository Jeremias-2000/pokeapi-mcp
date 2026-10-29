from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_project_root = Path(__file__).resolve().parents[4]
load_dotenv(_project_root / ".env", override=False)


class Settings(BaseSettings):
    """Single source of truth for environment configuration."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_prefix="",
        extra="ignore",
    )

    mcp_host: str = Field(default="127.0.0.1", min_length=1)
    mcp_port: int = Field(default=8000, ge=1, le=65535)
    mcp_reload: bool = False
    pokeapi_base_url: str = "https://pokeapi.co/api/v2"
    pokeapi_timeout: float = Field(default=10.0, gt=0)

    # Rate-limiting: maximum tool calls per caller per sliding window.
    rate_limit_max_calls: int = Field(default=30, ge=1)
    rate_limit_window_seconds: float = Field(default=60.0, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
