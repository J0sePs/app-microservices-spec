"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the withdrawal-soles service."""

    app_name: str = "withdrawal-soles"
    environment: str = "local"
    database_url: str = (
        "postgresql+asyncpg://withdrawal:withdrawal@localhost:5432/withdrawal_soles_db"
    )
    user_service_url: str = "http://localhost:8080"
    users_service_url: str | None = None
    transaction_service_url: str = "http://localhost:8080"
    wallet_service_url: str = "http://18.228.136.200"
    user_service_timeout_seconds: float = 2.0
    users_service_timeout_seconds: float = 2.0
    transaction_service_timeout_seconds: float = 3.0
    wallet_service_timeout_seconds: float = 2.0
    http_max_attempts: int = 3
    http_backoff_seconds: float = 0.2
    business_timezone: str = "America/Lima"
    wallet_jwt_secret: str = "dev-only-change-me"
    wallet_jwt_issuer: str = "billetera-dev"
    wallet_jwt_subject: str = "retiros"
    wallet_jwt_ttl_seconds: int = 60
    users_jwt_secret: str = "dev-only-change-me"
    users_jwt_issuer: str = "billetera-dev"
    users_jwt_subject: str = "billetera-service"
    users_jwt_ttl_seconds: int = 60
    auth_jwt_secret: str = "dev-only-change-me"
    auth_jwt_issuer: str = "billetera-dev"
    auth_jwt_algorithms: str = "HS256"
    auth_jwt_allowed_subjects: str = "retiros"

    @property
    def users_base_url(self) -> str:
        """Base URL for the published users contract."""

        return self.users_service_url or self.user_service_url

    @property
    def auth_jwt_algorithm_list(self) -> list[str]:
        """Parse the allowed algorithms from the comma-separated setting."""

        return [
            value.strip()
            for value in self.auth_jwt_algorithms.split(",")
            if value.strip()
        ]

    @property
    def auth_jwt_subject_set(self) -> set[str]:
        """Parse the allowed inbound token subjects."""

        return {
            value.strip()
            for value in self.auth_jwt_allowed_subjects.split(",")
            if value.strip()
        }

    model_config = SettingsConfigDict(
        env_prefix="WITHDRAWAL_SOLES_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for the process."""

    return Settings()
