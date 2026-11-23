"""Structured API errors. Every error response has the shape {"error": {"code", "message", "details"}}."""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("ddn.errors")


class APIError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: object | None = None):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.details = details


def _body(code: str, message: str, details: object | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


_DEFAULT_CODES = {
    400: "BAD_REQUEST", 401: "UNAUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND",
    409: "CONFLICT", 413: "PAYLOAD_TOO_LARGE", 415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR", 429: "RATE_LIMITED", 501: "NOT_IMPLEMENTED", 503: "UNAVAILABLE",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api_error(_: Request, exc: APIError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, str(exc.detail), exc.details))

    @app.exception_handler(StarletteHTTPException)  # also covers FastAPI's HTTPException and router-level 404/405
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code = _DEFAULT_CODES.get(exc.status_code, "ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(code, str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in e.get("loc", []) if p != "body"), "message": e.get("msg", "")}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content=_body("VALIDATION_ERROR", "Request validation failed.", details))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=_body("INTERNAL_ERROR", "An internal error occurred."))
