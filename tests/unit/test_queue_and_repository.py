"""Unit tests for queue delivery and tenant-scoped persistence."""

from __future__ import annotations

import pytest
from karta import repository as repo
from karta.events import AgentEvent, EventType, utc_now
from karta.models import UsageSummary
from karta.queue import InMemoryTaskQueue, TaskMessage
from sqlalchemy.engine import Engine


def test_in_memory_queue_recovery_redelivers() -> None:
    """In-flight messages are returned to the ready queue on recovery."""
    queue = InMemoryTaskQueue()
    message = TaskMessage("task-1", "tenant-a", "corr-1")
    queue.enqueue(message)
    assert queue.dequeue(timeout=0.01) == message
    assert queue.recover() == 1
    assert queue.dequeue(timeout=0.01) == message


@pytest.fixture()
def seeded(engine: Engine) -> tuple[str, str]:
    """Create a tenant project and task directly in the database."""
    with engine.begin() as connection:
        repo.create_project(
            connection, "tenant-a", "project-a", "Project A", "/tmp/project-a", utc_now()
        )
        repo.create_task(
            connection,
            "tenant-a",
            "task-a",
            "project-a",
            "coding",
            "1.0.0",
            "Write a file",
            "/tmp/project-a",
            "idem-a",
            utc_now(),
        )
    return "project-a", "task-a"


def test_repository_hides_cross_tenant_rows(engine: Engine, seeded: tuple[str, str]) -> None:
    """Reads scoped to another tenant cannot observe existing rows."""
    project_id, task_id = seeded
    with engine.begin() as connection:
        assert repo.get_project(connection, "tenant-b", project_id) is None
        assert repo.get_task(connection, "tenant-b", task_id) is None
        assert repo.find_task_by_idempotency(connection, "tenant-b", "idem-a") is None
        assert repo.list_projects(connection, "tenant-b") == []
        assert repo.list_tasks(connection, "tenant-b") == []


def test_repository_appends_monotonic_events_and_usage(
    engine: Engine, seeded: tuple[str, str]
) -> None:
    """Event sequences are contiguous and usage is tenant scoped."""
    _, task_id = seeded
    with engine.begin() as connection:
        for sequence in (1, 2):
            repo.append_event(
                connection,
                AgentEvent(
                    tenant_id="tenant-a",
                    task_id=task_id,
                    session_id=task_id,
                    sequence=sequence,
                    event_type=EventType.MESSAGE_DELTA,
                    payload={"delta": "x"},
                ),
            )
        with pytest.raises(ValueError, match="Expected event sequence 3"):
            repo.append_event(
                connection,
                AgentEvent(
                    tenant_id="tenant-a",
                    task_id=task_id,
                    session_id=task_id,
                    sequence=5,
                    event_type=EventType.MESSAGE_DELTA,
                ),
            )
        repo.insert_usage(
            connection,
            "tenant-a",
            task_id,
            "usage-1",
            UsageSummary(input_tokens=1, output_tokens=2, total_tokens=3),
            utc_now(),
        )
    with engine.begin() as connection:
        events = repo.list_events(connection, "tenant-a", task_id)
        assert [event["sequence"] for event in events] == [1, 2]
        assert repo.list_events(connection, "tenant-b", task_id) == []
        usage = repo.list_usage(connection, "tenant-a", task_id)
        assert usage[0]["total_tokens"] == 3
        assert repo.list_usage(connection, "tenant-b", task_id) == []


def test_repository_rejects_cross_tenant_event_write(
    engine: Engine, seeded: tuple[str, str]
) -> None:
    """Appending an event under the wrong tenant is refused."""
    _, task_id = seeded
    with engine.begin() as connection, pytest.raises(PermissionError):
        repo.append_event(
            connection,
            AgentEvent(
                tenant_id="tenant-b",
                task_id=task_id,
                session_id=task_id,
                sequence=1,
                event_type=EventType.TASK_STARTED,
            ),
        )
