"""FastAPI application entrypoint.

Besides wiring the routers, this module installs:

* ``CORSMiddleware`` using ``settings.cors_origins`` (issue #15), and
* exception handlers that return one consistent JSON error envelope for 404
  and 422 responses (issue #15).

Error envelope
--------------

Every handled error response has this top-level shape::

    {"error": {"code": "<machine_code>", "message": "<human message>", "details": <null | list>}}

* 404 (any ``HTTPException`` with status 404, including an unknown route):
  ``code`` is ``"not_found"``, ``details`` is ``null``.
* 422 (``RequestValidationError``): ``code`` is ``"validation_error"`` and
  ``details`` is the list of per-field errors from Pydantic.
* Other ``HTTPException`` statuses reuse the same envelope with a status-derived
  ``code`` (e.g. ``409`` -> ``"conflict"``).

A generic handler for unhandled 500s is deliberately out of scope here (#28).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.routers import analytics, exercises, goals, sessions

settings = get_settings()

app = FastAPI(title="Gym Exercise Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

#: HTTP status code -> stable machine-readable error code.
_ERROR_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
}


def _envelope(
    code: str, message: str, details: object | None = None
) -> dict[str, object]:
    return {"error": {"code": code, "message": message, "details": details}}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code = _ERROR_CODES.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(code, message),
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_envelope(
            "validation_error",
            "Request validation failed",
            jsonable_encoder(exc.errors()),
        ),
    )


app.include_router(exercises.router)
app.include_router(sessions.router)
app.include_router(goals.router)
app.include_router(analytics.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
