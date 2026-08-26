"""Application configuration.

Everything is environment-driven. Nothing here has a real credential as a
default, and nothing here reads a secret from a file that git can see.
See SECURITY.md.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings, sourced from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Database ───────────────────────────────────────────────────────────
    postgres_user: str = "slotsight"
    # Not a credential — a deliberately obvious placeholder for a throwaway
    # local database that holds nothing but synthetic data. The real value comes
    # from the environment, and in Azure the password is generated at provision
    # time and read from Key Vault. Flagged by bandit's S105, which cannot tell
    # a placeholder from a secret; the check is right to be suspicious.
    postgres_password: str = "change-me-local-only"  # noqa: S105
    postgres_db: str = "slotsight"
    postgres_host: str = "db"
    postgres_port: int = 5432

    database_url: str | None = Field(
        default=None,
        description="Full SQLAlchemy URL. Overrides the individual postgres_* parts.",
    )

    # ── Azure OpenAI ───────────────────────────────────────────────────────
    # REQUIRED for /api/chat only. The analytics endpoints never touch this.
    #
    # There is deliberately NO api-key setting. Auth is Entra ID via
    # DefaultAzureCredential, so there is no key to leak. See SECURITY.md.
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str = "2024-10-21"

    # ── Application ────────────────────────────────────────────────────────
    log_level: str = "info"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    property_name: str = "Neon Palms Casino Resort"
    property_short_name: str = "Neon Palms"

    # ── Synthetic data generator ───────────────────────────────────────────
    seed_random_seed: int = 20251107
    seed_machine_count: int = 840
    seed_days_of_history: int = 180

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_url(self) -> str:
        """Assemble the async SQLAlchemy URL if one wasn't given outright."""
        if self.database_url:
            # Accept a plain postgres:// URL (what Azure hands you) and upgrade
            # it to the async driver, which is what we actually need.
            url = self.database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def azure_openai_configured(self) -> bool:
        """True when /api/chat has what it needs to even attempt a call."""
        return bool(self.azure_openai_endpoint and self.azure_openai_deployment)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton. Call this, don't instantiate Settings()."""
    return Settings()
