"""Structured agent event contract for kartā.

The same JSON shape is produced by the TypeScript Pi runtime and persisted by
the Python control plane. The legacy schema-1 JSONL record is derived
downstream from these events; it is deliberately not emitted here (ADR-012).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """Normalized event types emitted while a task executes."""

    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    MESSAGE_DELTA = "message.delta"
    MESSAGE_COMPLETE = "message.complete"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    USAGE_RECORDED = "usage.recorded"


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string ending in ``Z``."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class AgentEvent(BaseModel):
    """Tenant-scoped, ordered event emitted during a task."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    event_type: EventType
    occurred_at: str = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    trace_id: str | None = None


class EventPage(BaseModel):
    """Ordered page of persisted events returned by the API."""

    tenant_id: str
    task_id: str
    events: list[AgentEvent]
    next_sequence: int
