"""Application configuration loaded from environment / .env file."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "changeme-in-production"

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://interviewcraft:interviewcraft@localhost:5432/interviewcraft"
    )

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"

    # ── CORS ───────────────────────────────────────────────────────────────────
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
        # Production Vercel frontend — required for cross-origin auth cookie flow
        "https://interviewcraft-ten.vercel.app",
    ]

    # ── Anthropic (Claude) ─────────────────────────────────────────────────────
    anthropic_api_key: str = ""

    # ── Deepgram (STT + Budget TTS) ────────────────────────────────────────────
    deepgram_api_key: str = ""

    # ── ElevenLabs (TTS) ──────────────────────────────────────────────────────
    elevenlabs_api_key: str = ""

    # ── JWT ────────────────────────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # ── Rate limiting (Redis-backed) ───────────────────────────────────────────
    rate_limit_auth_requests: int = 5
    rate_limit_auth_window_seconds: int = 60

    @model_validator(mode="after")
    def validate_production_secret_key(self) -> "Settings":
        """Reject the default secret_key in non-development environments."""
        if self.app_env != "development" and self.secret_key == "changeme-in-production":
            raise ValueError(
                "SECRET_KEY must be set to a secure random value in non-development environments. "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return self

    # ── Google OAuth (optional at MVP) ─────────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""

    # ── Email / SMTP (optional — digests disabled if not configured) ───────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@interviewcraft.app"
    smtp_from_name: str = "InterviewCraft"
    smtp_tls: bool = True  # STARTTLS on port 587


settings = Settings()
