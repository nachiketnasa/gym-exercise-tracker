"""Settings, CORS, and the JSON error envelope (issue #15)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic_settings import SettingsConfigDict

from app import config
from app.main import app

ALLOWED_ORIGIN = "http://localhost:5173"
DISALLOWED_ORIGIN = "http://evil.example.com"

client = TestClient(app)


# --- settings --------------------------------------------------------------


def test_defaults_when_only_database_url_is_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/x")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    clean = SettingsConfigDict(env_file=None, case_sensitive=False, extra="ignore")
    monkeypatch.setattr(config.Settings, "model_config", clean)

    settings = config.Settings()

    assert settings.database_url == "postgresql://u:p@localhost:5432/x"
    assert settings.cors_origins == ["http://localhost:5173"]
    assert settings.environment == "local"


def test_cors_origins_override_comma_separated(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/x")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    clean = SettingsConfigDict(env_file=None, case_sensitive=False, extra="ignore")
    monkeypatch.setattr(config.Settings, "model_config", clean)

    assert config.Settings().cors_origins == ["http://a.test", "http://b.test"]


def test_cors_origins_override_json_list(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/x")
    monkeypatch.setenv("CORS_ORIGINS", '["http://a.test"]')
    clean = SettingsConfigDict(env_file=None, case_sensitive=False, extra="ignore")
    monkeypatch.setattr(config.Settings, "model_config", clean)

    assert config.Settings().cors_origins == ["http://a.test"]


def test_missing_database_url_raises_error_naming_the_variable(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    clean = SettingsConfigDict(env_file=None, case_sensitive=False, extra="ignore")
    monkeypatch.setattr(config.Settings, "model_config", clean)

    config.get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            config.get_settings()
    finally:
        config.get_settings.cache_clear()


# --- CORS -----------------------------------------------------------------


def test_preflight_from_allowed_origin_is_permitted():
    response = client.options(
        "/exercises",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code in (200, 204)
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_preflight_from_disallowed_origin_is_not_echoed():
    response = client.options(
        "/exercises",
        headers={
            "Origin": DISALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") != DISALLOWED_ORIGIN


# --- error envelope ------------------------------------------------------


def test_unknown_route_returns_404_envelope():
    response = client.get("/definitely-not-a-route")

    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == "not_found"
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert body["error"]["details"] is None


def test_unknown_id_returns_404_envelope(db_session):
    from app.db import get_session

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as c:
            response = c.get("/exercises/999999")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Exercise 999999 not found",
            "details": None,
        }
    }


def test_validation_error_returns_same_envelope_shape():
    # /sessions rejects a non-date `date` with a RequestValidationError (422).
    response = client.post("/sessions", json={"date": "not-a-date"})

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["error"]["details"], list)
    assert body["error"]["details"], "per-field validation details are preserved"
    assert any("date" in str(item.get("loc", "")) for item in body["error"]["details"])


def test_health_still_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
