"""Configuration management for the bot — Railway deployment ready."""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Discord
    discord_token: str = Field(..., env="DISCORD_TOKEN")
    discord_application_id: str = Field(..., env="DISCORD_APPLICATION_ID")
    
    # Database (Railway provides postgresql://, we need postgresql+asyncpg://)
    database_url: str = Field(..., env="DATABASE_URL")
    database_echo: bool = Field(False, env="DATABASE_ECHO")
    
    # Redis
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    # Sentry
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    
    # Bot Configuration
    bot_prefix: str = Field("/", env="BOT_PREFIX")
    bot_owner_id: str = Field(..., env="BOT_OWNER_ID")
    bot_log_level: str = Field("INFO", env="BOT_LOG_LEVEL")
    
    # Environment
    environment: str = Field("production", env="ENVIRONMENT")
    
    # UMSU Configuration
    umsu_nim_pattern: str = Field(r"^\d{10}$", env="UMSU_NIM_PATTERN")
    umsu_prodi_codes: str = Field("TI,SI,SD", env="UMSU_PRODI_CODES")
    umsu_min_attendance: int = Field(10, env="UMSU_MIN_ATTENDANCE")
    
    # Attendance Configuration
    attendance_code_length: int = Field(6, env="ATTENDANCE_CODE_LENGTH")
    attendance_code_expiry_minutes: int = Field(15, env="ATTENDANCE_CODE_EXPIRY_MINUTES")
    attendance_session_timeout_minutes: int = Field(120, env="ATTENDANCE_SESSION_TIMEOUT_MINUTES")
    
    # Grading Configuration
    late_penalty_per_hour: int = Field(5, env="LATE_PENALTY_PER_HOUR")
    late_penalty_max_percent: int = Field(50, env="LATE_PENALTY_MAX_PERCENT")
    late_submission_max_hours: int = Field(24, env="LATE_SUBMISSION_MAX_HOURS")
    
    # Gamification Configuration
    exp_base: int = Field(100, env="EXP_BASE")
    exp_level_multiplier: float = Field(1.5, env="EXP_LEVEL_MULTIPLIER")
    max_level: int = Field(50, env="MAX_LEVEL")
    
    # Rate Limiting
    rate_limit_commands_per_minute: int = Field(10, env="RATE_LIMIT_COMMANDS_PER_MINUTE")
    rate_limit_commands_per_hour: int = Field(100, env="RATE_LIMIT_COMMANDS_PER_HOUR")
    
    @property
    def prodi_codes(self) -> list[str]:
        """Parse prodi codes from comma-separated string."""
        return self.umsu_prodi_codes.split(",")
    
    def get_async_database_url(self) -> str:
        """Convert DATABASE_URL to async format for SQLAlchemy.
        
        Railway provides: postgresql://...
        We need: postgresql+asyncpg://...
        """
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


_settings = None


def get_settings() -> Settings:
    """Get application settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
