"""Typed application settings (issue #15).

All backend configuration is read from the environment (and a local ``.env``
file) through one :class:`Settings` object. Use :func:`get_settings` to obtain
the cached instance.

Environment variables
---------------------

============== ============================================ ========================================
Field          Env var                                      Notes
============== ============================================ ========================================
``database_url``   ``DATABASE_URL``                         Required. No default. If unset, creating
                                                            the settings raises a ``RuntimeError``
                                                            naming ``DATABASE_URL``.
``cors_origins``   ``CORS_ORIGINS``                         Optional. Defaults to
                                                            ``["http://localhost:5173"]`` (the Vite
                                                            dev server). Override with either a
                                                            comma-separated list
                                                            (``http://a.com,http://b.com``) or a
                                                            JSON array (``["http://a.com"]``).
``environment``    ``ENVIRONMENT``                          Optional. Defaults to ``local``
                                                            (e.g. ``local`` / ``dev`` / ``prod``).
============== ============================================ ========================================

Wiring ``database_url`` into the actual engine/session module is out of scope
here (that is issue #3); :mod:`app.db` still reads ``DATABASE_URL`` directly.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_DIR.parent

#: The frontend Vite dev server origin, used when ``CORS_ORIGINS`` is unset.
DEFAULT_CORS_ORIGINS: list[str] = ["http://localhost:5173"]


class Settings(BaseSettings):
    """All backend configuration, populated from the environment / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    #: SQLAlchemy / Postgres connection URL. Read from ``DATABASE_URL``.
    #: Required, no default.
    database_url: str

    #: Origins allowed by CORS. Read from ``CORS_ORIGINS``; defaults to the
    #: Vite dev server.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: list(DEFAULT_CORS_ORIGINS)
    )

    #: Deployment environment name. Read from ``ENVIRONMENT``.
    environment: str = "local"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        """Accept a comma-separated string or a JSON array from the env var."""
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return list(DEFAULT_CORS_ORIGINS)
            if text.startswith("["):
                return json.loads(text)
            return [part.strip() for part in text.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the cached :class:`Settings`, raising a clear error if invalid."""
    try:
        return Settings()
    except ValidationError as exc:
        missing = {
            str(err["loc"][0]).lower()
            for err in exc.errors()
            if err["type"] == "missing"
        }
        if "database_url" in missing:
            raise RuntimeError(
                "DATABASE_URL is not set. Export it or put it in a .env file, "
                "e.g. DATABASE_URL=postgresql://gym:gym@localhost:5432/gym_tracker"
            ) from exc
        raise
