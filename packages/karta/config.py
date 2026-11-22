"""Environment-driven configuration for the kartā control plane."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    """Validated runtime settings shared by the API, CLI and worker.

    Attributes:
        database_url: SQLAlchemy-compatible database URL.
        redis_url: Redis URL used by the task queue.
        marga_base_url: OpenAI-compatible base URL of the external Marga service.
        marga_api_key: Internal credential used by the runtime when calling Marga.
        runtime_url: Base URL of the Pi runtime service.
        internal_token: Shared secret for control-plane to runtime calls.
        api_token: Shared local-mode API token; required for the API process.
        tenant_id: Default single-tenant identifier for Milestone 1.
        queue_backend: ``memory`` or ``redis`` task queue implementation.
        embed_worker: Whether the API process also runs the worker loop.
        projects_root: Directory containing local project workspaces.
        profiles_root: Directory containing declarative agent profiles.

    """

    database_url: str
    redis_url: str
    marga_base_url: str
    marga_api_key: str
    runtime_url: str
    internal_token: str
    api_token: str
    tenant_id: str
    queue_backend: str
    embed_worker: bool
    projects_root: Path
    profiles_root: Path

    @property
    def api_base_url(self) -> str:
        """Return the loopback API URL advertised to the CLI."""
        return os.environ.get("KARTA_API_URL", "http://127.0.0.1:8100")


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build settings from an environment mapping.

    Args:
        env: Environment mapping; ``os.environ`` is used when omitted.

    Returns:
        Validated settings with trailing slashes removed from URLs.

    Raises:
        ValueError: When a required value is blank.

    """
    source: Mapping[str, str] = os.environ if env is None else env
    values = {
        "database_url": source.get(
            "KARTA_DATABASE_URL",
            "sqlite:///" + str(Path.home() / ".local/share/karta/karta.db"),
        ),
        "redis_url": source.get("KARTA_REDIS_URL", "redis://127.0.0.1:56379/0"),
        "marga_base_url": source.get("KARTA_MARGA_URL", "http://127.0.0.1:8010/v1"),
        "marga_api_key": source.get("KARTA_MARGA_API_KEY", ""),
        "runtime_url": source.get("KARTA_RUNTIME_URL", "http://127.0.0.1:8101"),
        "internal_token": source.get("KARTA_INTERNAL_TOKEN", ""),
        "api_token": source.get("KARTA_API_TOKEN", ""),
        "tenant_id": source.get("KARTA_TENANT_ID", "local"),
        "queue_backend": source.get("KARTA_QUEUE_BACKEND", "redis"),
        "embed_worker": source.get("KARTA_EMBED_WORKER", "0").lower()
        in {"1", "true", "yes", "on"},
        "projects_root": source.get(
            "KARTA_PROJECTS_ROOT", str(Path.home() / ".local/share/karta/projects")
        ),
        "profiles_root": source.get(
            "KARTA_PROFILES_ROOT", str(Path(__file__).resolve().parents[2] / "agent-profiles")
        ),
    }
    for key in ("database_url", "redis_url", "marga_base_url", "runtime_url", "tenant_id"):
        if not values[key].strip():
            raise ValueError(f"{key} must not be blank")
    if values["queue_backend"] not in {"memory", "redis"}:
        raise ValueError("KARTA_QUEUE_BACKEND must be 'memory' or 'redis'")
    return Settings(
        database_url=values["database_url"],
        redis_url=values["redis_url"],
        marga_base_url=values["marga_base_url"].rstrip("/"),
        marga_api_key=values["marga_api_key"],
        runtime_url=values["runtime_url"].rstrip("/"),
        internal_token=values["internal_token"],
        api_token=values["api_token"],
        tenant_id=values["tenant_id"],
        queue_backend=values["queue_backend"],
        embed_worker=values["embed_worker"],
        projects_root=Path(values["projects_root"]),
        profiles_root=Path(values["profiles_root"]),
    )
