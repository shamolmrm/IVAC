from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_DATA_KEY = "ZGV2ZWxvcG1lbnQta2V5LW5vdC1mb3ItcHJvZHVjdGk="  # public, development only


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

    # Outgoing SMS (mobile OTP). Disabled until a provider is configured; see app/core/sms.py.
    sms_provider: str = ""
    sms_api_key: str = ""
    sms_sender_id: str = ""
    otp_ttl_seconds: int = 5 * 60
    otp_max_attempts: int = 5
    otp_resend_seconds: int = 60
    otp_per_hour: int = 5

    # Field encryption (passport / NID numbers). 32 random bytes, base64. The default is a
    # public development key; production refuses to start with it (see app.main).
    data_encryption_key: str = DEV_DATA_KEY

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
