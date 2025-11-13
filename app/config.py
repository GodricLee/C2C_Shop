"""Application configuration module."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import BaseSettings, EmailStr, Field, validator


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables."""

    app_name: str = Field("C2C Backend", description="Application display name")
    app_env: str = Field("dev", description="Deployment environment label")
    db_url: str = Field(..., env="DB_URL", description="SQLAlchemy database URL")
    jwt_secret: str = Field(..., env="JWT_SECRET", description="JWT signing secret")
    jwt_algorithm: str = Field("HS256", description="JWT signing algorithm")
    jwt_exp_hours: int = Field(24, description="JWT expiration window in hours")
    twofa_channels: List[str] = Field(
        ["email", "sms", "totp"],
        env="TWOFA_CHANNELS",
        description="Enabled 2FA delivery channels",
    )
    cors_origins: List[str] = Field(
        ["https://c2cshop.retr28.com", "http://localhost:5173"],
        description="Allowed CORS origins",
    )
    member_discount_rate: float = Field(
        0.05,
        description="Default shopper membership discount rate (5% off)",
    )
    admin_default_email: EmailStr = Field(
        "lz2300109991@gmail.com", description="Seed admin email for demo data"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

        @classmethod
        def parse_env_var(cls, field_name: str, raw_value: str):
            if field_name == "twofa_channels":
                return raw_value
            return super().parse_env_var(field_name, raw_value)

    @validator("twofa_channels", pre=True)
    def parse_twofa_channels(cls, value: object) -> List[str]:
        default_channels = cls.__fields__["twofa_channels"].default  # type: ignore[attr-defined]
        if value in (None, ""):
            return list(default_channels)
        if isinstance(value, str):
            parsed = [item.strip() for item in value.split(",") if item.strip()]
            return parsed or list(default_channels)
        if isinstance(value, list):
            return value
        return list(default_channels)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()  # type: ignore[arg-type]
