"""FastAPI application entry point.  Run:  uvicorn app.main:app --reload   (from the backend/ folder)"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.api.routers import admin, analysis, auth, dashboard, feedback, system, users
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.db.init_db import create_all
from app.db.session import SessionLocal
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.accounts import ensure_initial_admin, ensure_roles
from app.services.registry import sync_registry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

DESCRIPTION = """
Deepfake News Detection System - a student research prototype.

**What the analysis results mean.** The text module scores writing-pattern similarity to the articles it was trained on;
it does not verify facts. The image module reports forensic *indicators* (Error Level Analysis and metadata), not a
verdict. Video, multimodal, evidence and URL-credibility modules are not implemented and return `501`.
Check `GET /api/v1/models` for the live status of every module.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.auto_create_tables:
        create_all()
    with SessionLocal() as db:
        ensure_roles(db)
        sync_registry(db)
        ensure_initial_admin(db)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=s.app_name, version=s.app_version, description=DESCRIPTION, lifespan=lifespan)
    install_error_handlers(app)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    app.add_middleware(RateLimitMiddleware)
    # Added last so it is the outermost layer: even rate-limit (429) responses carry the CORS headers.
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origin_list, allow_credentials=False,
                       allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])

    for module in (system, auth, users, analysis, dashboard, feedback, admin):
        app.include_router(module.router, prefix="/api/v1")
    return app


app = create_app()
