"""Application service coordinating projects, profiles, tasks and execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.engine import Engine

from . import repository as repo
from .auth import Principal
from .config import Settings
from .errors import ApiError
from .events import AgentEvent, EventPage, EventType, utc_now
from .models import (
    ExecutionRequest,
    ExecutionResult,
    ProfileList,
    ProfileRead,
    ProjectCreate,
    ProjectList,
    ProjectRead,
    TaskCreate,
    TaskList,
    TaskRead,
    UsageSummary,
)
from .profiles import CodingProfile, load_profiles
from .queue import TaskMessage, TaskQueue
from .runtime_client import RuntimeClient


def _project_read(row: dict[str, Any]) -> ProjectRead:
    return ProjectRead(**row)


def _task_read(row: dict[str, Any]) -> TaskRead:
    return TaskRead(**row)


def _profile_read(row: dict[str, Any]) -> ProfileRead:
    return ProfileRead(
        id=row["id"],
        version=row["version"],
        tenant_id=row["tenant_id"],
        content_hash=row["content_hash"],
        definition=json.loads(row["definition"]),
    )


class TaskService:
    """Tenant-scoped application service used by the API and worker."""

    def __init__(
        self,
        settings: Settings,
        engine: Engine,
        queue: TaskQueue,
        runtime: RuntimeClient,
    ) -> None:
        """Initialise the service.

        Args:
            settings: Validated control-plane settings.
            engine: SQLAlchemy engine.
            queue: Task queue used for enqueue and worker delivery.
            runtime: Client for the Pi runtime HTTP API.

        """
        self.settings = settings
        self.engine = engine
        self.queue = queue
        self.runtime = runtime

    def create_project(self, principal: Principal, request: ProjectCreate) -> ProjectRead:
        """Create a project owned by the authenticated tenant.

        Args:
            principal: Authenticated caller.
            request: Validated project request.

        Returns:
            Created project.

        Raises:
            ApiError: When the workspace path is invalid.

        """
        workspace = Path(request.workspace_path or self.settings.projects_root / request.name)
        workspace = workspace.expanduser()
        if not workspace.is_dir():
            raise ApiError(
                400, "workspace_not_found", f"Workspace directory does not exist: {workspace}"
            )
        project_id = str(uuid4())
        with self.engine.begin() as connection:
            return _project_read(
                repo.create_project(
                    connection,
                    principal.tenant_id,
                    project_id,
                    request.name,
                    str(workspace.resolve()),
                    utc_now(),
                )
            )

    def list_projects(self, principal: Principal) -> ProjectList:
        """List projects visible to the authenticated tenant."""
        with self.engine.begin() as connection:
            rows = repo.list_projects(connection, principal.tenant_id)
        return ProjectList(projects=[_project_read(row) for row in rows])

    def list_profiles(self, principal: Principal) -> ProfileList:
        """List stored profile versions for the authenticated tenant."""
        with self.engine.begin() as connection:
            rows = repo.list_profiles(connection, principal.tenant_id)
        return ProfileList(profiles=[_profile_read(row) for row in rows])

    def _available_profile(self, profile_id: str, version: str) -> CodingProfile:
        """Load and validate a filesystem profile at the requested version."""
        profiles = load_profiles(self.settings.profiles_root)
        profile = profiles.get(profile_id)
        if profile is None:
            raise ApiError(404, "profile_not_found", f"Unknown agent profile: {profile_id}")
        if profile.version != version:
            raise ApiError(
                409,
                "profile_version_mismatch",
                f"Profile {profile_id} has version {profile.version}, not {version}",
            )
        return profile

    def create_task(
        self,
        principal: Principal,
        request: TaskCreate,
        correlation_id: str,
    ) -> TaskRead:
        """Create a durable task and enqueue it for execution.

        Args:
            principal: Authenticated caller.
            request: Validated task request; tenant is never taken from it.
            correlation_id: Request correlation identifier.

        Returns:
            Created or existing task.

        Raises:
            ApiError: When the project or profile is invalid.

        """
        profile = self._available_profile(request.agent_profile_id, request.agent_profile_version)
        with self.engine.begin() as connection:
            if request.idempotency_key:
                existing = repo.find_task_by_idempotency(
                    connection, principal.tenant_id, request.idempotency_key
                )
                if existing is not None:
                    return _task_read(existing)
            project = repo.get_project(connection, principal.tenant_id, request.project_id)
            if project is None:
                raise ApiError(404, "project_not_found", "Project does not exist for this tenant")
            workspace = Path(project["workspace_path"])
            if not workspace.is_dir():
                raise ApiError(400, "workspace_not_found", "Project workspace is unavailable")
            repo.save_profile(
                connection,
                principal.tenant_id,
                profile.id,
                profile.version,
                profile.content_hash(),
                json.dumps(profile.definition(), sort_keys=True, separators=(",", ":")),
                utc_now(),
            )
            task_id = str(uuid4())
            task = repo.create_task(
                connection,
                principal.tenant_id,
                task_id,
                request.project_id,
                profile.id,
                profile.version,
                request.prompt,
                str(workspace.resolve()),
                request.idempotency_key,
                utc_now(),
            )
            repo.append_event(
                connection,
                AgentEvent(
                    tenant_id=principal.tenant_id,
                    task_id=task_id,
                    session_id=task_id,
                    sequence=1,
                    event_type=EventType.TASK_CREATED,
                    payload={"profile_id": profile.id, "profile_version": profile.version},
                    correlation_id=correlation_id,
                ),
            )
        self.queue.enqueue(
            TaskMessage(
                task_id=task_id,
                tenant_id=principal.tenant_id,
                correlation_id=correlation_id,
            )
        )
        return _task_read(task)

    def get_task(self, principal: Principal, task_id: str) -> TaskRead:
        """Return one task for the authenticated tenant."""
        with self.engine.begin() as connection:
            row = repo.get_task(connection, principal.tenant_id, task_id)
        if row is None:
            raise ApiError(404, "task_not_found", "Task does not exist for this tenant")
        return _task_read(row)

    def list_tasks(self, principal: Principal) -> TaskList:
        """List tasks for the authenticated tenant."""
        with self.engine.begin() as connection:
            rows = repo.list_tasks(connection, principal.tenant_id)
        return TaskList(tasks=[_task_read(row) for row in rows])

    def event_page(
        self,
        principal: Principal,
        task_id: str,
        after_sequence: int = 0,
        limit: int = 200,
    ) -> EventPage:
        """Return a tenant-verified page of task events."""
        with self.engine.begin() as connection:
            if not repo.task_exists(connection, principal.tenant_id, task_id):
                raise ApiError(404, "task_not_found", "Task does not exist for this tenant")
            rows = repo.list_events(connection, principal.tenant_id, task_id, after_sequence, limit)
        events = [
            AgentEvent(
                tenant_id=row["tenant_id"],
                task_id=row["task_id"],
                session_id=row["task_id"],
                sequence=int(row["sequence"]),
                event_id=row["event_id"],
                event_type=row["event_type"],
                occurred_at=row["occurred_at"],
                payload=json.loads(row["payload"]),
                correlation_id=row["correlation_id"],
            )
            for row in rows
        ]
        next_sequence = max((event.sequence for event in events), default=after_sequence)
        return EventPage(
            tenant_id=principal.tenant_id,
            task_id=task_id,
            events=events,
            next_sequence=next_sequence,
        )

    def execute(self, tenant_id: str, task_id: str, correlation_id: str) -> None:
        """Execute one queued task through the Pi runtime.

        Called by the worker with values from a queue message, never with
        values supplied by an external client.

        Args:
            tenant_id: Tenant that owns the task.
            task_id: Durable task identifier.
            correlation_id: Correlation identifier propagated to the runtime.

        """
        with self.engine.begin() as connection:
            task = repo.get_task(connection, tenant_id, task_id)
            if task is None:
                return
            if task["status"] not in {"queued", "running"}:
                return
            session_id = task_id
            repo.update_task_status(connection, tenant_id, task_id, "running", utc_now())
            repo.append_event(
                connection,
                AgentEvent(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    session_id=session_id,
                    sequence=repo.next_sequence(connection, tenant_id, task_id),
                    event_type=EventType.TASK_STARTED,
                    payload={"correlation_id": correlation_id},
                    correlation_id=correlation_id,
                ),
            )
            profile = load_profiles(self.settings.profiles_root).get(task["agent_profile_id"])
            if profile is None:
                self._fail_task(
                    tenant_id, task_id, session_id, correlation_id, "profile_unavailable"
                )
                return
            request = ExecutionRequest(
                task_id=task_id,
                tenant_id=tenant_id,
                session_id=session_id,
                prompt=task["prompt"],
                workspace_path=task["workspace_path"],
                profile=profile.definition(),
                marga_base_url=self.settings.marga_base_url,
                model=profile.model_policy.strong,
                api_key=self.settings.marga_api_key,
                correlation_id=correlation_id,
                limits={
                    "max_iterations": profile.limits.max_iterations,
                    "max_tool_calls": profile.limits.max_tool_calls,
                    "max_execution_minutes": profile.limits.max_execution_minutes,
                },
            )

        try:
            result = self.runtime.execute(request)
        except ApiError as exc:
            self._fail_task(tenant_id, task_id, session_id, correlation_id, exc.message)
            return
        self._persist_result(tenant_id, task_id, session_id, correlation_id, result)

    def _persist_result(
        self,
        tenant_id: str,
        task_id: str,
        session_id: str,
        correlation_id: str,
        result: ExecutionResult,
    ) -> None:
        """Persist runtime events, usage and final task outcome."""
        with self.engine.begin() as connection:
            offset = repo.next_sequence(connection, tenant_id, task_id) - 1
            for index, event in enumerate(result.events, start=1):
                event.tenant_id = tenant_id
                event.task_id = task_id
                event.session_id = session_id
                event.sequence = offset + index
                event.correlation_id = correlation_id
                repo.append_event(connection, event)
            next_sequence = repo.next_sequence(connection, tenant_id, task_id)
            if result.usage.total_tokens > 0:
                repo.insert_usage(
                    connection,
                    tenant_id,
                    task_id,
                    str(uuid4()),
                    UsageSummary.model_validate(result.usage),
                    utc_now(),
                )
                repo.append_event(
                    connection,
                    AgentEvent(
                        tenant_id=tenant_id,
                        task_id=task_id,
                        session_id=session_id,
                        sequence=next_sequence,
                        event_type=EventType.USAGE_RECORDED,
                        payload=result.usage.model_dump(),
                        correlation_id=correlation_id,
                    ),
                )
                next_sequence += 1
            if result.status == "failed":
                repo.append_event(
                    connection,
                    AgentEvent(
                        tenant_id=tenant_id,
                        task_id=task_id,
                        session_id=session_id,
                        sequence=next_sequence,
                        event_type=EventType.TASK_FAILED,
                        payload={"error": result.error or "Runtime execution failed"},
                        correlation_id=correlation_id,
                    ),
                )
                repo.update_task_status(
                    connection,
                    tenant_id,
                    task_id,
                    "failed",
                    utc_now(),
                    result=result.final_text,
                    error=result.error or "Runtime execution failed",
                )
                return
            repo.append_event(
                connection,
                AgentEvent(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    session_id=session_id,
                    sequence=next_sequence,
                    event_type=EventType.TASK_COMPLETED,
                    payload={"stop_reason": result.stop_reason},
                    correlation_id=correlation_id,
                ),
            )
            repo.update_task_status(
                connection,
                tenant_id,
                task_id,
                "completed",
                utc_now(),
                result=result.final_text,
            )

    def _fail_task(
        self,
        tenant_id: str,
        task_id: str,
        session_id: str,
        correlation_id: str,
        error: str,
    ) -> None:
        """Mark a task failed and append a failure event."""
        with self.engine.begin() as connection:
            repo.append_event(
                connection,
                AgentEvent(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    session_id=session_id,
                    sequence=repo.next_sequence(connection, tenant_id, task_id),
                    event_type=EventType.TASK_FAILED,
                    payload={"error": error},
                    correlation_id=correlation_id,
                ),
            )
            repo.update_task_status(
                connection, tenant_id, task_id, "failed", utc_now(), error=error
            )
