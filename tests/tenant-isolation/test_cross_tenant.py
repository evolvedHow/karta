"""Cross-tenant isolation release-blocker tests.

A failure in this module blocks the Milestone 1 release. The two clients below
share the same database and queue but carry tokens for different tenants.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from karta.queue import InMemoryTaskQueue


def _register_project(client: TestClient, headers: dict[str, str], workspace: Path) -> str:
    """Register a workspace as a project."""
    response = client.post(
        "/api/v1/projects",
        json={"name": "tenant-repo", "workspace_path": str(workspace)},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_tenant_b_cannot_read_tenant_a_task(
    client: TestClient,
    other_client: TestClient,
    queue: InMemoryTaskQueue,
    auth_headers: dict[str, str],
    workspace: Path,
) -> None:
    """Task detail, event history and event stream are tenant scoped."""
    project_id = _register_project(client, auth_headers, workspace)
    created = client.post(
        "/api/v1/tasks",
        json={"prompt": "Create a file", "project_id": project_id},
        headers=auth_headers,
    )
    task_id = created.json()["id"]
    message = queue.dequeue(timeout=0.2)
    assert message is not None
    client.app.state.service.execute(  # type: ignore[attr-defined]
        message.tenant_id, message.task_id, message.correlation_id
    )

    other_headers = {"Authorization": "Bearer test-api-token"}
    assert other_client.get(f"/api/v1/tasks/{task_id}", headers=other_headers).status_code == 404
    assert (
        other_client.get(f"/api/v1/tasks/{task_id}/events", headers=other_headers).status_code
        == 404
    )
    assert (
        other_client.get(
            f"/api/v1/tasks/{task_id}/events/stream", headers=other_headers
        ).status_code
        == 404
    )
    assert other_client.get("/api/v1/tasks", headers=other_headers).json()["tasks"] == []


def test_tenant_b_cannot_use_tenant_a_project(
    client: TestClient,
    other_client: TestClient,
    auth_headers: dict[str, str],
    workspace: Path,
) -> None:
    """Referencing another tenant's project identifier is rejected."""
    project_id = _register_project(client, auth_headers, workspace)
    response = other_client.post(
        "/api/v1/tasks",
        json={"prompt": "Create a file", "project_id": project_id},
        headers={"Authorization": "Bearer test-api-token"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "project_not_found"


def test_profiles_are_not_shared_between_tenants(
    client: TestClient,
    other_client: TestClient,
    auth_headers: dict[str, str],
    workspace: Path,
) -> None:
    """A profile pinned by tenant A is invisible to tenant B."""
    project_id = _register_project(client, auth_headers, workspace)
    client.post(
        "/api/v1/tasks",
        json={"prompt": "Create a file", "project_id": project_id},
        headers=auth_headers,
    )
    other_headers = {"Authorization": "Bearer test-api-token"}
    assert other_client.get("/api/v1/profiles", headers=other_headers).json()["profiles"] == []
