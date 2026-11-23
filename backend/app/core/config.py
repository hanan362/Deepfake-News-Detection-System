"""Application settings, loaded from environment variables and an optional .env file."""
from __future__ import annotations

import logging
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> project root is three levels above this folder
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PLACEHOLDER_SECRET = "change-me-in-production"

logger = logging.getLogger("ddn.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(str(PROJECT_ROOT / ".env"),), extra="ignore")

    app_name: str = "Deepfake News Detection System"
    app_version: str = "0.1.0"
    environment: str = "development"  # development | production | test

    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'storage' / 'app.db').as_posix()}"
    secret_key: str = PLACEHOLDER_SECRET
    access_token_expire_minutes: int = 60
    password_reset_expire_minutes: int = 30
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    storage_dir: Path = PROJECT_ROOT / "storage"
    models_dir: Path = PROJECT_ROOT / "ai_models" / "checkpoints"

    max_image_mb: int = 10
    max_image_pixels: int = 40_000_000
    max_video_mb: int = 100
    max_video_seconds: int = 180
    video_sample_frames: int = 16  # the number used when the decision thresholds were measured
    video_model_id: str = "hchcsuim/FFPP-Raw_1FPS_faces-expand-40-aligned_val-ds-celeb-df"

    rate_limit_per_minute: int = 120
    # Reading a news URL makes the server download a page for the user. It can be switched off, and each user is
    # limited so the endpoint cannot be used as a relay.
    url_fetch_enabled: bool = True
    # Evidence checking: a pretrained inference model, and optional published fact-checks (needs an API key).
    nli_model_id: str = "cross-encoder/nli-deberta-v3-small"
    evidence_enabled: bool = True
    corroboration_enabled: bool = True
    corroboration_timeout_seconds: float = 8.0
    corroboration_rate_limit_per_minute: int = 10
    clip_model_id: str = "openai/clip-vit-base-patch32"
    google_fact_check_api_key: str | None = None
    url_fetch_rate_limit_per_minute: int = 10
    auth_rate_limit_per_minute: int = 10

    # There is no e-mail service in the base install. In development the reset token can be
    # returned by the API so the flow can be tested; never enable this in production.
    expose_reset_token: bool = False

    # Optional first administrator, created at start-up when both values are present.
    admin_email: str | None = None
    admin_password: str | None = None

    # The baseline was trained on full articles (median ~380 words, 5th percentile ~70 words). Shorter text is
    # outside what it has seen, so it is declined instead of scored.
    text_confidence_threshold: float = 0.80
    min_text_tokens: int = 60
    max_text_chars: int = 50_000

    bcrypt_rounds: int = 12  # tests lower this for speed; keep >= 12 in real deployments
    # Create tables on start-up. Docker/production deployments run `python -m app.db.migrate` and set this to false.
    auto_create_tables: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.secret_key == PLACEHOLDER_SECRET:
        if s.is_production:
            raise RuntimeError("SECRET_KEY must be set to a strong random value in production.")
        s.secret_key = secrets.token_urlsafe(48)
        logger.warning(
            "SECRET_KEY is not set; using a random key for this process. "
            "Login sessions will end when the server restarts. Set SECRET_KEY in .env."
        )
    if s.is_production and s.expose_reset_token:
        raise RuntimeError("EXPOSE_RESET_TOKEN must not be enabled in production.")
    return s
