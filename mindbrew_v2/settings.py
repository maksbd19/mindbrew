from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

_FIELD_ENV = {
    "database_url": "DATABASE_URL",
    "nebius_api_key": "NEBIUS_API_KEY",
    "nebius_model": "NEBIUS_MODEL",
    "nebius_base_url": "NEBIUS_BASE_URL",
    "brewmind_offline": "BREWMIND_OFFLINE",
    "fba_python": "FBA_PYTHON",
    "biomni_data_path": "BIOMNI_DATA_PATH",
    "max_revisions": "MAX_REVISIONS",
}


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is missing or invalid."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    nebius_api_key: str
    nebius_model: str
    nebius_base_url: str
    brewmind_offline: bool
    fba_python: str
    biomni_data_path: str
    max_revisions: int


@lru_cache
def get_settings() -> Settings:
    if not ENV_FILE.is_file():
        raise ConfigurationError(
            f"Configuration file not found: {ENV_FILE}. "
            "Create it from .env.example and set all required values."
        )
    try:
        return Settings()
    except ValidationError as exc:
        missing = [
            _FIELD_ENV.get(str(err["loc"][0]), str(err["loc"][0]))
            for err in exc.errors()
            if err["type"] == "missing"
        ]
        if missing:
            detail = f"Missing required variables: {', '.join(missing)}"
        else:
            detail = str(exc)
        raise ConfigurationError(f"Invalid configuration in {ENV_FILE}. {detail}") from exc


def is_offline() -> bool:
    return get_settings().brewmind_offline
