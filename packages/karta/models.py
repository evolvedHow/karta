"""Pydantic request and response schemas for the kartā HTTP API.

Client-facing models never accept a ``tenant_id``; it is always derived from
the authenticated principal to prevent tenant spoofing.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .events import AgentEvent, EventPage  # noqa: F401 - re-exported for API consumers


class ProjectCreate(BaseModel):
    """Request body for creating a project."""

    name: str = Field(min_length=1, max_length=200)
    workspace_path: str | None = Field(default=None, max_length=4096)


class ProjectRead(BaseModel):
    """A project visible to the authenticated tenant."""

    id: str
    tenant_id: str
    name: str
    workspace_path: str
    created_at: str


class ProjectList(BaseModel):
    """Ordered list of projects."""

    projects: list[ProjectRead]


class TaskCreate(BaseModel):
    """Request body for starting a coding task."""

    prompt: str = Field(min_length=1, max_length=10000)
    project_id: str = Field(min_length=1)
    agent_profile_id: str = Field(default="coding", min_length=1)
    agent_profile_version: str = Field(default="1.0.0", min_length=1)
    idempotency_key: str | None = Field(default=None, max_length=200)


class TaskRead(BaseModel):
    """Durable state of a task."""

    id: str
    tenant_id: str
    project_id: str
    agent_profile_id: str
    agent_profile_version: str
    prompt: str
    status: str
    workspace_path: str
    result: str | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class TaskList(BaseModel):
    """Ordered list of tasks."""

    tasks: list[TaskRead]


class ProfileRead(BaseModel):
    """A validated, versioned agent profile."""

    id: str
    version: str
    tenant_id: str
    content_hash: str
    definition: dict[str, Any]


class ProfileList(BaseModel):
    """Available agent profiles."""

    profiles: list[ProfileRead]


class UsageSummary(BaseModel):
    """Token usage reported by the provider."""

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class UsageRead(BaseModel):
    """Persisted usage record for one task."""

    id: str
    tenant_id: str
    task_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    occurred_at: str


class ExecutionRequest(BaseModel):
    """Control-plane to runtime contract, sent over the internal HTTP API."""

    task_id: str
    tenant_id: str
    session_id: str
    prompt: str
    workspace_path: str
    profile: dict[str, Any]
    marga_base_url: str
    model: str
    api_key: str = Field(repr=False)
    correlation_id: str
    limits: dict[str, int] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    """Runtime to control-plane contract returned by ``POST /v1/execute``."""

    task_id: str
    status: Literal["completed", "failed"]
    final_text: str = ""
    stop_reason: str = "unknown"
    events: list[AgentEvent] = Field(default_factory=list)
    usage: UsageSummary = Field(default_factory=UsageSummary)
    error: str | None = None


class HealthRead(BaseModel):
    """Liveness or readiness response."""

    status: str
    version: str
    checks: dict[str, str] = Field(default_factory=dict)


class ApiErrorBody(BaseModel):
    """Structured error envelope."""

    error: dict[str, Any]
