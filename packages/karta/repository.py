"""Tenant-scoped persistence for projects, profiles, tasks, events and usage.

Every query in this module carries an explicit ``tenant_id`` predicate. The
control plane derived that value from the authenticated principal; it is never
accepted from a request body.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .events import AgentEvent
from .models import UsageSummary


def create_project(
    connection: Connection,
    tenant_id: str,
    project_id: str,
    name: str,
    workspace_path: str,
    created_at: str,
) -> dict[str, Any]:
    """Insert a project owned by ``tenant_id``."""
    connection.execute(
        text(
            "INSERT INTO projects (id, tenant_id, name, workspace_path, created_at) "
            "VALUES (:id, :tenant_id, :name, :workspace_path, :created_at)"
        ),
        {
            "id": project_id,
            "tenant_id": tenant_id,
            "name": name,
            "workspace_path": workspace_path,
            "created_at": created_at,
        },
    )
    row = get_project(connection, tenant_id, project_id)
    if row is None:
        raise RuntimeError("Project insert did not persist")
    return row


def get_project(connection: Connection, tenant_id: str, project_id: str) -> dict[str, Any] | None:
    """Return a project only when it belongs to ``tenant_id``."""
    row = connection.execute(
        text(
            "SELECT id, tenant_id, name, workspace_path, created_at "
            "FROM projects WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": project_id, "tenant_id": tenant_id},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_projects(connection: Connection, tenant_id: str) -> list[dict[str, Any]]:
    """Return all projects for ``tenant_id`` ordered by creation time."""
    rows = connection.execute(
        text(
            "SELECT id, tenant_id, name, workspace_path, created_at FROM projects "
            "WHERE tenant_id = :tenant_id ORDER BY created_at, id"
        ),
        {"tenant_id": tenant_id},
    ).mappings().all()
    return [dict(row) for row in rows]


def save_profile(
    connection: Connection,
    tenant_id: str,
    profile_id: str,
    version: str,
    content_hash: str,
    definition: str,
    created_at: str,
) -> None:
    """Persist an immutable profile version for ``tenant_id``."""
    connection.execute(
        text(
            "INSERT OR IGNORE INTO agent_profiles "
            "(id, version, tenant_id, content_hash, definition, created_at) "
            "VALUES (:id, :version, :tenant_id, :content_hash, :definition, :created_at)"
        ),
        {
            "id": profile_id,
            "version": version,
            "tenant_id": tenant_id,
            "content_hash": content_hash,
            "definition": definition,
            "created_at": created_at,
        },
    )


def get_profile(
    connection: Connection, tenant_id: str, profile_id: str, version: str
) -> dict[str, Any] | None:
    """Return a profile version only when it belongs to ``tenant_id``."""
    row = connection.execute(
        text(
            "SELECT id, version, tenant_id, content_hash, definition, created_at "
            "FROM agent_profiles WHERE id = :id AND version = :version "
            "AND tenant_id = :tenant_id"
        ),
        {"id": profile_id, "version": version, "tenant_id": tenant_id},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_profiles(connection: Connection, tenant_id: str) -> list[dict[str, Any]]:
    """Return the highest stored version of each profile for ``tenant_id``."""
    rows = connection.execute(
        text(
            "SELECT ap.id, ap.version, ap.tenant_id, ap.content_hash, ap.definition "
            "FROM agent_profiles ap "
            "JOIN (SELECT id, MAX(version) AS version FROM agent_profiles "
            "WHERE tenant_id = :tenant_id GROUP BY id) latest "
            "ON latest.id = ap.id AND latest.version = ap.version "
            "WHERE ap.tenant_id = :tenant_id ORDER BY ap.id"
        ),
        {"tenant_id": tenant_id},
    ).mappings().all()
    return [dict(row) for row in rows]


def create_task(
    connection: Connection,
    tenant_id: str,
    task_id: str,
    project_id: str,
    profile_id: str,
    profile_version: str,
    prompt: str,
    workspace_path: str,
    idempotency_key: str | None,
    now: str,
) -> dict[str, Any]:
    """Insert a queued task owned by ``tenant_id``."""
    connection.execute(
        text(
            "INSERT INTO tasks (id, tenant_id, project_id, agent_profile_id, "
            "agent_profile_version, prompt, status, idempotency_key, workspace_path, "
            "created_at, updated_at) VALUES (:id, :tenant_id, :project_id, :profile_id, "
            ":profile_version, :prompt, 'queued', :idempotency_key, :workspace_path, "
            ":now, :now)"
        ),
        {
            "id": task_id,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "profile_id": profile_id,
            "profile_version": profile_version,
            "prompt": prompt,
            "idempotency_key": idempotency_key,
            "workspace_path": workspace_path,
            "now": now,
        },
    )
    row = get_task(connection, tenant_id, task_id)
    if row is None:
        raise RuntimeError("Task insert did not persist")
    return row


def get_task(connection: Connection, tenant_id: str, task_id: str) -> dict[str, Any] | None:
    """Return a task only when it belongs to ``tenant_id``."""
    row = connection.execute(
        text(
            "SELECT id, tenant_id, project_id, agent_profile_id, agent_profile_version, "
            "prompt, status, workspace_path, result, error, created_at, updated_at "
            "FROM tasks WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": task_id, "tenant_id": tenant_id},
    ).mappings().first()
    return dict(row) if row is not None else None


def find_task_by_idempotency(
    connection: Connection, tenant_id: str, idempotency_key: str
) -> dict[str, Any] | None:
    """Return an existing task for a tenant-scoped idempotency key."""
    row = connection.execute(
        text(
            "SELECT id, tenant_id, project_id, agent_profile_id, agent_profile_version, "
            "prompt, status, workspace_path, result, error, created_at, updated_at "
            "FROM tasks WHERE tenant_id = :tenant_id AND idempotency_key = :key"
        ),
        {"tenant_id": tenant_id, "key": idempotency_key},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_tasks(connection: Connection, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return the most recent tasks for ``tenant_id``."""
    rows = connection.execute(
        text(
            "SELECT id, tenant_id, project_id, agent_profile_id, agent_profile_version, "
            "prompt, status, workspace_path, result, error, created_at, updated_at "
            "FROM tasks WHERE tenant_id = :tenant_id "
            "ORDER BY created_at DESC, id DESC LIMIT :limit"
        ),
        {"tenant_id": tenant_id, "limit": limit},
    ).mappings().all()
    return [dict(row) for row in rows]


def update_task_status(
    connection: Connection,
    tenant_id: str,
    task_id: str,
    status: str,
    now: str,
    result: str | None = None,
    error: str | None = None,
) -> dict[str, Any] | None:
    """Update task status and outcome, scoped to ``tenant_id``."""
    connection.execute(
        text(
            "UPDATE tasks SET status = :status, result = :result, error = :error, "
            "updated_at = :now WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {
            "status": status,
            "result": result,
            "error": error,
            "now": now,
            "id": task_id,
            "tenant_id": tenant_id,
        },
    )
    return get_task(connection, tenant_id, task_id)


def task_exists(connection: Connection, tenant_id: str, task_id: str) -> bool:
    """Return whether ``task_id`` exists within ``tenant_id``."""
    return (
        connection.execute(
            text("SELECT 1 FROM tasks WHERE id = :id AND tenant_id = :tenant_id"),
            {"id": task_id, "tenant_id": tenant_id},
        ).first()
        is not None
    )


def append_event(connection: Connection, event: AgentEvent) -> None:
    """Append an event with a tenant-verified monotonic sequence.

    Args:
        connection: Active database connection, normally inside a transaction.
        event: Fully populated event including tenant and sequence.

    Raises:
        PermissionError: When the task does not belong to the event's tenant.
        ValueError: When the event's sequence is not the next expected value.

    """
    if not task_exists(connection, event.tenant_id, event.task_id):
        raise PermissionError("Task does not belong to tenant")
    row = connection.execute(
        text(
            "SELECT COALESCE(MAX(sequence), 0) AS last_sequence FROM task_events "
            "WHERE tenant_id = :tenant_id AND task_id = :task_id"
        ),
        {"tenant_id": event.tenant_id, "task_id": event.task_id},
    ).mappings().first()
    expected = int(row["last_sequence"]) + 1
    if event.sequence != expected:
        raise ValueError(f"Expected event sequence {expected}, got {event.sequence}")
    connection.execute(
        text(
            "INSERT INTO task_events (tenant_id, task_id, sequence, event_id, "
            "event_type, occurred_at, payload, correlation_id) VALUES (:tenant_id, "
            ":task_id, :sequence, :event_id, :event_type, :occurred_at, :payload, "
            ":correlation_id)"
        ),
        {
            "tenant_id": event.tenant_id,
            "task_id": event.task_id,
            "sequence": event.sequence,
            "event_id": event.event_id,
            "event_type": str(event.event_type),
            "occurred_at": event.occurred_at,
            "payload": json.dumps(event.payload, separators=(",", ":")),
            "correlation_id": event.correlation_id,
        },
    )


def next_sequence(connection: Connection, tenant_id: str, task_id: str) -> int:
    """Return the next sequence number for a tenant-verified task."""
    if not task_exists(connection, tenant_id, task_id):
        raise PermissionError("Task does not belong to tenant")
    row = connection.execute(
        text(
            "SELECT COALESCE(MAX(sequence), 0) AS last_sequence FROM task_events "
            "WHERE tenant_id = :tenant_id AND task_id = :task_id"
        ),
        {"tenant_id": tenant_id, "task_id": task_id},
    ).mappings().first()
    return int(row["last_sequence"]) + 1


def list_events(
    connection: Connection,
    tenant_id: str,
    task_id: str,
    after_sequence: int = 0,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return ordered events for a task, strictly after ``after_sequence``."""
    rows = connection.execute(
        text(
            "SELECT tenant_id, task_id, sequence, event_id, event_type, occurred_at, "
            "payload, correlation_id FROM task_events WHERE tenant_id = :tenant_id "
            "AND task_id = :task_id "
            "AND sequence > :after ORDER BY sequence LIMIT :limit"
        ),
        {
            "tenant_id": tenant_id,
            "task_id": task_id,
            "after": after_sequence,
            "limit": limit,
        },
    ).mappings().all()
    return [dict(row) for row in rows]


def insert_usage(
    connection: Connection,
    tenant_id: str,
    task_id: str,
    usage_id: str,
    usage: UsageSummary,
    occurred_at: str,
) -> None:
    """Persist provider usage for a tenant-verified task."""
    if not task_exists(connection, tenant_id, task_id):
        raise PermissionError("Task does not belong to tenant")
    connection.execute(
        text(
            "INSERT INTO usage_events (id, tenant_id, task_id, input_tokens, "
            "output_tokens, total_tokens, occurred_at) VALUES (:id, :tenant_id, "
            ":task_id, :input, :output, :total, :occurred_at)"
        ),
        {
            "id": usage_id,
            "tenant_id": tenant_id,
            "task_id": task_id,
            "input": usage.input_tokens,
            "output": usage.output_tokens,
            "total": usage.total_tokens,
            "occurred_at": occurred_at,
        },
    )


def list_usage(
    connection: Connection, tenant_id: str, task_id: str | None = None
) -> list[dict[str, Any]]:
    """Return usage records for ``tenant_id``, optionally filtered by task."""
    statement = (
        "SELECT id, tenant_id, task_id, input_tokens, output_tokens, total_tokens, "
        "occurred_at FROM usage_events WHERE tenant_id = :tenant_id"
    )
    params: dict[str, Any] = {"tenant_id": tenant_id}
    if task_id is not None:
        statement += " AND task_id = :task_id"
        params["task_id"] = task_id
    statement += " ORDER BY occurred_at, id"
    rows = connection.execute(text(statement), params).mappings().all()
    return [dict(row) for row in rows]
