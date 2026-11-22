"""Integration tests for the API, worker execution and event replay."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from karta.queue import InMemoryTaskQueue


def _create_project(client: TestClient, headers: dict[str, str], workspace: Path) -> str:
    """Register a project and return its identifier."""
    response = client.post(
        "/api/v1/projects",
        json={"name": "test-repo", "workspace_path": str(workspace)},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _drain_one(queue: InMemoryTaskQueue, client: TestClient) -> None:
    """Execute one queued task through the app service."""
    message = queue.dequeue(timeout=0.2)
    assert message is not None
    service = client.app.state.service  # type: ignore[attr-defined]
    service.execute(message.tenant_id, message.task_id, message.correlation_id)


def test_health_and_ready_are_public(client: TestClient) -> None:
    """Liveness and readiness do not require authentication."""
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"] == "ok"


def test_openapi_documents_the_control_plane(client: TestClient) -> None:
    """Every documented endpoint is present in the generated OpenAPI schema."""
    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/health",
        "/api/v1/projects",
        "/api/v1/profiles",
        "/api/v1/tasks",
        "/api/v1/tasks/{task_id}/events",
        "/api/v1/tasks/{task_id}/events/stream",
    ):
        assert path in paths


def test_task_runs_against_local_test_repository(
    client: TestClient,
    queue: InMemoryTaskQueue,
    fake_runtime: Any,
    auth_headers: dict[str, str],
    workspace: Path,
) -> None:
    """A queued coding task is executed, persisted and replayable."""
    project_id = _create_project(client, auth_headers, workspace)
    created = client.post(
        "/api/v1/tasks",
        json={"prompt": "Create a file", "project_id": project_id},
        headers=auth_headers,
    )
    assert created.status_code == 202, created.text
    task_id = created.json()["id"]

    _drain_one(queue, client)

    task = client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers).json()
    assert task["status"] == "completed"
    assert task["result"] == "done"

    events = client.get(
        f"/api/v1/tasks/{task_id}/events", headers=auth_headers
    ).json()["events"]
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert events[0]["event_type"] == "task.created"
    assert events[-1]["event_type"] == "task.completed"
    assert any(event["event_type"] == "usage.recorded" for event in events)
    assert all(event["tenant_id"] == "tenant-a" for event in events)
    assert all(event["correlation_id"] for event in events)

    assert fake_runtime.requests[0].workspace_path == str(workspace.resolve())
    assert fake_runtime.requests[0].model == "strong"

    resumed = client.get(
        f"/api/v1/tasks/{task_id}/events",
        params={"after": 2},
        headers=auth_headers,
    ).json()["events"]
    assert all(event["sequence"] > 2 for event in resumed)


def test_idempotency_key_returns_same_task(
    client: TestClient,
    auth_headers: dict[str, str],
    workspace: Path,
) -> None:
    """Repeated submissions with one key do not create duplicate tasks."""
    project_id = _create_project(client, auth_headers, workspace)
    payload = {
        "prompt": "Create a file",
        "project_id": project_id,
        "idempotency_key": "stable-key",
    }
    first = client.post("/api/v1/tasks", json=payload, headers=auth_headers).json()
    second = client.post("/api/v1/tasks", json=payload, headers=auth_headers).json()
    assert first["id"] == second["id"]
    assert len(client.get("/api/v1/tasks", headers=auth_headers).json()["tasks"]) == 1


def test_profiles_endpoint_lists_persisted_profile(
    client: TestClient, auth_headers: dict[str, str], workspace: Path
) -> None:
    """A profile pinned by task creation is visible through the API."""
    project_id = _create_project(client, auth_headers, workspace)
    client.post(
        "/api/v1/tasks",
        json={"prompt": "Create a file", "project_id": project_id},
        headers=auth_headers,
    )
    listed = client.get("/api/v1/profiles", headers=auth_headers).json()
    assert [profile["id"] for profile in listed["profiles"]] == ["coding"]
    assert listed["profiles"][0]["version"] == "1.0.0"
    assert len(listed["profiles"][0]["content_hash"]) == 64


def test_sse_stream_replays_events(
    client: TestClient,
    queue: InMemoryTaskQueue,
    auth_headers: dict[str, str],
    workspace: Path,
) -> None:
    """The SSE endpoint emits ordered event frames for a completed task."""
    project_id = _create_project(client, auth_headers, workspace)
    created = client.post(
        "/api/v1/tasks",
        json={"prompt": "Create a file", "project_id": project_id},
        headers=auth_headers,
    )
    task_id = created.json()["id"]
    _drain_one(queue, client)
    with client.stream(
        "GET", f"/api/v1/tasks/{task_id}/events/stream", headers=auth_headers
    ) as response:
        body = response.read().decode("utf-8")
    assert "event_type" in body
    assert body.count("id: ") >= 1
