"""Database engine creation and deterministic SQL migration runner."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from .config import Settings, load_settings
from .events import utc_now

_MIGRATION_TABLE_SQL = (
    "CREATE TABLE IF NOT EXISTS schema_migrations ("
    "version TEXT PRIMARY KEY, "
    "checksum TEXT NOT NULL, "
    "applied_at TEXT NOT NULL)"
)


def create_db_engine(settings: Settings) -> Engine:
    """Create a SQLAlchemy engine for the configured database.

    Args:
        settings: Validated control-plane settings.

    Returns:
        Engine configured for PostgreSQL or in-process SQLite.

    """
    url = settings.database_url
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
    return create_engine(url, pool_pre_ping=True, future=True)


def _statements(sql: str) -> Iterable[str]:
    """Yield non-empty SQL statements from a migration file.

    Args:
        sql: Raw migration contents.

    Yields:
        Individual statements without trailing semicolons.

    """
    for part in sql.split(";"):
        candidate = part.strip()
        if candidate and not all(line.strip().startswith("--") for line in candidate.splitlines()):
            yield candidate


def run_migrations(engine: Engine, migrations_dir: Path | str) -> list[str]:
    """Apply pending SQL migrations in filename order.

    A checksum guard prevents silent edits to an already-applied migration.
    The whole operation is safe to run on every process start.

    Args:
        engine: SQLAlchemy engine pointing at the target database.
        migrations_dir: Directory containing ``*.sql`` migration files.

    Returns:
        Sorted list of all applied migration versions.

    Raises:
        RuntimeError: When an applied migration's checksum has changed.

    """
    directory = Path(migrations_dir)
    with engine.begin() as connection:
        connection.execute(text(_MIGRATION_TABLE_SQL))
        rows = connection.execute(
            text("SELECT version, checksum FROM schema_migrations")
        ).mappings().all()
    applied = {row["version"]: row["checksum"] for row in rows}

    for path in sorted(directory.rglob("*.sql")):
        version = path.stem
        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        if version in applied:
            if applied[version] != checksum:
                raise RuntimeError(f"Migration {version} changed after it was applied")
            continue
        with engine.begin() as connection:
            for statement in _statements(sql):
                connection.execute(text(statement))
            connection.execute(
                text(
                    "INSERT INTO schema_migrations (version, checksum, applied_at) "
                    "VALUES (:version, :checksum, :applied_at)"
                ),
                {"version": version, "checksum": checksum, "applied_at": utc_now()},
            )
        applied[version] = checksum
    return sorted(applied)


def run_migrations_cli() -> None:
    """Apply all pending migrations from the command line."""
    settings = load_settings()
    engine = create_db_engine(settings)
    root = Path(__file__).resolve().parents[2]
    versions = run_migrations(engine, root / "migrations")
    print(f"Applied migrations: {', '.join(versions) or 'none'}")
    engine.dispose()
