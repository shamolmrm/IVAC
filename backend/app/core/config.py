from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Visa Assistant API"
    brand_name: str = "Visa Assistant"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]
    public_url: str = "https://ivac.supersoftltd.com"

    database_url: str = "postgresql+psycopg://ivac:ivac@localhost:5433/ivac"
    redis_url: str = "redis://localhost:6380/0"

    # Sessions (short: this system holds passport data)
    session_cookie_name: str = "ivac_session"
    session_ttl_days: int = 7

    # Abuse protection
    auth_rate_limit_per_minute: int = 10  # per IP, all auth endpoints
    login_failures_per_email: int = 5  # then the account is locked for the window below
    login_lock_seconds: int = 15 * 60

    # Outgoing email. Disabled until SMTP_HOST and MAIL_FROM are set.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.mail_from)

    @property
    def cookie_secure(self) -> bool:
        return self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()
