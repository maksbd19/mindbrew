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
    "max_revisions": "MAX_REVISIONS",
    "literature_retrieval_enabled": "LITERATURE_RETRIEVAL_ENABLED",
    "lamin_public_dbs": "LAMIN_PUBLIC_DBS",
    "literature_max_ontology_hits": "LITERATURE_MAX_ONTOLOGY_HITS",
    "literature_max_artifact_hits": "LITERATURE_MAX_ARTIFACT_HITS",
    "literature_max_pubmed_hits": "LITERATURE_MAX_PUBMED_HITS",
    "literature_max_crossref_hits": "LITERATURE_MAX_CROSSREF_HITS",
    "literature_context_max_chars": "LITERATURE_CONTEXT_MAX_CHARS",
    "progress_heartbeat_interval_sec": "PROGRESS_HEARTBEAT_INTERVAL_SEC",
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
    max_revisions: int
    literature_retrieval_enabled: bool = True
    lamin_public_dbs: str = "laminlabs/cellxgene"
    literature_max_ontology_hits: int = 5
    literature_max_artifact_hits: int = 5
    literature_max_pubmed_hits: int = 8
    literature_max_crossref_hits: int = 5
    literature_context_max_chars: int = 8000
    progress_heartbeat_interval_sec: int = 15

    def lamin_public_db_list(self) -> list[str]:
        return [item.strip() for item in self.lamin_public_dbs.split(",") if item.strip()]


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
