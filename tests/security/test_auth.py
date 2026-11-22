"""Security tests for authentication and untrusted client input."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_missing_and_invalid_tokens_are_rejected(client: TestClient) -> None:
    """All API resources require a valid bearer token."""
    endpoints = (
        "/api/v1/projects",
        "/api/v1/profiles",
        "/api/v1/tasks",
    )
    for path in endpoints:
        assert client.get(path).status_code == 401
        assert (
            client.get(path, headers={"Authorization": "Bearer wrong-token"}).status_code == 401
        )
        assert client.get(path, headers={"Authorization": "Basic abc"}).status_code == 401


def test_client_cannot_choose_tenant(
    client: TestClient, auth_headers: dict[str, str], workspace: Path
) -> None:
    """A tenant identifier supplied in the request body is ignored."""
    project = client.post(
        "/api/v1/projects",
        json={
            "name": "test-repo",
            "workspace_path": str(workspace),
            "tenant_id": "tenant-b",
        },
        headers=auth_headers,
    )
    assert project.status_code == 201
    assert project.json()["tenant_id"] == "tenant-a"

    task = client.post(
        "/api/v1/tasks",
        json={
            "prompt": "Create a file",
            "project_id": project.json()["id"],
            "tenant_id": "tenant-b",
        },
        headers=auth_headers,
    )
    assert task.status_code == 202
    assert task.json()["tenant_id"] == "tenant-a"


def test_error_envelope_includes_correlation_id(client: TestClient) -> None:
    """Structured errors carry the request correlation identifier."""
    response = client.get(
        "/api/v1/tasks/missing",
        headers={"Authorization": "Bearer test-api-token", "X-Correlation-ID": "corr-123"},
    )
    assert response.status_code == 404
    assert response.headers["X-Correlation-ID"] == "corr-123"
    assert response.json()["error"]["correlation_id"] == "corr-123"
