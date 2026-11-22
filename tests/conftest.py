"""Shared fixtures for the kartā control-plane test suite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from karta.api import create_app
from karta.config import Settings, load_settings
from karta.db import create_db_engine, run_migrations
from karta.events import AgentEvent, EventType
from karta.models import ExecutionRequest, ExecutionResult, UsageSummary
from karta.queue import InMemoryTaskQueue
from sqlalchemy.engine import Engine


class FakeRuntime:
    """Deterministic stand-in for the TypeScript Pi runtime."""

    def __init__(self) -> None:
        """Initialise an empty request log."""
        self.requests: list[ExecutionRequest] = []

    def health(self) -> bool:
        """Report readiness."""
        return True

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Return a canned successful execution with two normalized events."""
        self.requests.append(request)
        base = {
            "tenant_id": request.tenant_id,
            "task_id": request.task_id,
            "session_id": request.session_id,
            "correlation_id": request.correlation_id,
        }
        events = [
            AgentEvent(
                **base,
                sequence=1,
                event_type=EventType.MESSAGE_DELTA,
                payload={"delta": "done"},
            ),
            AgentEvent(
                **base,
                sequence=2,
                event_type=EventType.MESSAGE_COMPLETE,
                payload={},
            ),
        ]
        return ExecutionResult(
            task_id=request.task_id,
            status="completed",
            final_text="done",
            stop_reason="stop",
            events=events,
            usage=UsageSummary(input_tokens=10, output_tokens=5, total_tokens=15),
            error=None,
        )

    def close(self) -> None:
        """No resources to release."""


@pytest.fixture()
def test_settings() -> Settings:
    """Return isolated settings with an in-memory queue and a fixed token."""
    return load_settings(
        {
            "KARTA_DATABASE_URL": "sqlite:///:memory:",
            "KARTA_QUEUE_BACKEND": "memory",
            "KARTA_API_TOKEN": "test-api-token",
            "KARTA_INTERNAL_TOKEN": "test-internal-token",
            "KARTA_TENANT_ID": "tenant-a",
            "KARTA_RUNTIME_URL": "http://127.0.0.1:8101",
        }
    )


@pytest.fixture()
def engine(test_settings: Settings) -> Engine:
    """Create an in-memory SQLAlchemy engine."""
    created = create_db_engine(test_settings)
    migrations = Path(__file__).resolve().parents[1] / "migrations"
    run_migrations(created, migrations)
    yield created
    created.dispose()


@pytest.fixture()
def queue() -> InMemoryTaskQueue:
    """Create an isolated in-memory task queue."""
    return InMemoryTaskQueue()


@pytest.fixture()
def fake_runtime() -> FakeRuntime:
    """Create a deterministic runtime client."""
    return FakeRuntime()


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    """Return valid authorization headers for tenant A."""
    return {"Authorization": "Bearer test-api-token"}


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Create a local test repository workspace."""
    directory = tmp_path / "test-repo"
    directory.mkdir()
    (directory / "README.md").write_text("initial", encoding="utf-8")
    return directory


@pytest.fixture()
def client(
    test_settings: Settings,
    engine: Engine,
    queue: InMemoryTaskQueue,
    fake_runtime: FakeRuntime,
) -> Any:
    """Create a test client wired to isolated control-plane resources."""
    app = create_app(test_settings, engine=engine, queue=queue, runtime=fake_runtime)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def other_client(
    test_settings: Settings,
    engine: Engine,
    queue: InMemoryTaskQueue,
    fake_runtime: FakeRuntime,
) -> Any:
    """Create a second API instance whose token belongs to a different tenant."""
    settings = test_settings.__class__(
        **{**test_settings.__dict__, "tenant_id": "tenant-b"}
    )
    app = create_app(settings, engine=engine, queue=queue, runtime=fake_runtime)
    with TestClient(app) as test_client:
        yield test_client
