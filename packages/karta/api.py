"""FastAPI control-plane application for kartā."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import text

from . import __version__
from .auth import Principal, require_scope
from .config import Settings, load_settings
from .db import create_db_engine, run_migrations
from .errors import ApiError
from .models import (
    ApiErrorBody,
    HealthRead,
    ProfileList,
    ProjectCreate,
    ProjectList,
    ProjectRead,
    TaskCreate,
    TaskList,
    TaskRead,
)
from .queue import InMemoryTaskQueue, RedisTaskQueue, TaskQueue
from .runtime_client import RuntimeClient
from .tasks import TaskService
from .worker import run_worker_loop


def _build_queue(settings: Settings) -> TaskQueue:
    """Create the configured task queue."""
    if settings.queue_backend == "memory":
        return InMemoryTaskQueue()
    return RedisTaskQueue.from_settings(settings)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise shared resources and start an embedded worker when requested."""
    settings: Settings = app.state.settings
    if not hasattr(app.state, "engine"):
        app.state.engine = create_db_engine(settings)
    repository_root = Path(__file__).resolve().parents[2]
    run_migrations(app.state.engine, repository_root / "migrations")
    if not hasattr(app.state, "queue"):
        app.state.queue = _build_queue(settings)
    if hasattr(app.state, "queue") and settings.queue_backend == "redis":
        app.state.queue.recover()
    if not hasattr(app.state, "runtime"):
        app.state.runtime = RuntimeClient(settings.runtime_url, settings.internal_token)
    app.state.service = TaskService(settings, app.state.engine, app.state.queue, app.state.runtime)
    stop = asyncio.Event()
    worker_task: asyncio.Task[None] | None = None
    if settings.embed_worker:
        worker_task = asyncio.create_task(
            asyncio.to_thread(run_worker_loop, app.state.service, app.state.queue, stop)
        )
    yield
    stop.set()
    if worker_task is not None:
        await worker_task
    app.state.runtime.close()
    app.state.queue.close()
    app.state.engine.dispose()


def create_app(
    settings: Settings | None = None,
    engine: Any | None = None,
    queue: TaskQueue | None = None,
    runtime: RuntimeClient | None = None,
) -> FastAPI:
    """Build the FastAPI application.

    Args:
        settings: Optional settings override for tests.
        engine: Optional SQLAlchemy engine override.
        queue: Optional task queue override.
        runtime: Optional runtime client override.

    Returns:
        Configured FastAPI application with OpenAPI documentation enabled.

    """
    resolved = settings or load_settings()
    app = FastAPI(
        title="kartā control plane",
        version=__version__,
        description="Tenant-scoped task control plane for the kartā agent platform.",
        lifespan=_lifespan,
    )
    app.state.settings = resolved
    if engine is not None:
        app.state.engine = engine
    if queue is not None:
        app.state.queue = queue
    if runtime is not None:
        app.state.runtime = runtime

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next: Any) -> Any:
        """Attach a correlation identifier to every request and response."""
        correlation = request.headers.get("x-correlation-id") or str(uuid4())
        request.state.correlation_id = correlation
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        """Render structured JSON errors."""
        body = ApiErrorBody(
            error={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "correlation_id": getattr(request.state, "correlation_id", None),
            }
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @app.get("/health", response_model=HealthRead, tags=["ops"])
    async def health() -> HealthRead:
        """Report process liveness."""
        return HealthRead(status="ok", version=__version__)

    @app.get("/ready", response_model=HealthRead, tags=["ops"])
    async def ready(request: Request) -> JSONResponse:
        """Report database and queue readiness."""
        checks: dict[str, str] = {}
        healthy = True
        try:
            with request.app.state.engine.begin() as connection:
                connection.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "unavailable"
            healthy = False
        try:
            ping = getattr(request.app.state.queue, "_client", None)
            if ping is not None:
                ping.ping()
            checks["queue"] = "ok"
        except Exception:
            checks["queue"] = "unavailable"
            healthy = False
        payload = HealthRead(
            status="ok" if healthy else "unavailable", version=__version__, checks=checks
        )
        return JSONResponse(
            status_code=200 if healthy else 503,
            content=payload.model_dump(),
        )

    @app.get("/api/v1/projects", response_model=ProjectList, tags=["projects"])
    async def list_projects(
        request: Request,
        principal: Principal = Depends(require_scope("projects:read")),
    ) -> ProjectList:
        """List projects owned by the authenticated tenant."""
        return request_app(request).service.list_projects(principal)

    @app.post(
        "/api/v1/projects",
        response_model=ProjectRead,
        status_code=201,
        tags=["projects"],
    )
    async def create_project(
        request_body: ProjectCreate,
        request: Request,
        principal: Principal = Depends(require_scope("projects:write")),
    ) -> ProjectRead:
        """Create a project in an existing local workspace."""
        return request_app(request).service.create_project(principal, request_body)

    @app.get("/api/v1/profiles", response_model=ProfileList, tags=["profiles"])
    async def list_profiles(
        request: Request,
        principal: Principal = Depends(require_scope("profiles:read")),
    ) -> ProfileList:
        """List stored agent profiles for the authenticated tenant."""
        return request_app(request).service.list_profiles(principal)

    @app.post("/api/v1/tasks", response_model=TaskRead, status_code=202, tags=["tasks"])
    async def create_task(
        request_body: TaskCreate,
        request: Request,
        principal: Principal = Depends(require_scope("tasks:write")),
    ) -> TaskRead:
        """Create and enqueue a coding task."""
        return request_app(request).service.create_task(
            principal, request_body, request.state.correlation_id
        )

    @app.get("/api/v1/tasks", response_model=TaskList, tags=["tasks"])
    async def list_tasks(
        request: Request,
        principal: Principal = Depends(require_scope("tasks:read")),
    ) -> TaskList:
        """List tasks for the authenticated tenant."""
        return request_app(request).service.list_tasks(principal)

    @app.get("/api/v1/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
    async def get_task(
        task_id: str,
        request: Request,
        principal: Principal = Depends(require_scope("tasks:read")),
    ) -> TaskRead:
        """Return one task for the authenticated tenant."""
        return request_app(request).service.get_task(principal, task_id)

    @app.get("/api/v1/tasks/{task_id}/events", tags=["tasks"])
    async def get_events(
        task_id: str,
        request: Request,
        after: int = Query(default=0, ge=0),
        limit: int = Query(default=200, ge=1, le=1000),
        principal: Principal = Depends(require_scope("tasks:read")),
    ) -> dict[str, Any]:
        """Return a tenant-verified page of task events."""
        page = request_app(request).service.event_page(principal, task_id, after, limit)
        return page.model_dump()

    @app.get("/api/v1/tasks/{task_id}/events/stream", tags=["tasks"])
    async def stream_events(
        task_id: str,
        request: Request,
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        principal: Principal = Depends(require_scope("tasks:read")),
    ) -> StreamingResponse:
        """Stream task events as SSE with sequence-based resume support."""
        service: TaskService = request_app(request).service
        service.get_task(principal, task_id)
        after = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0

        async def generator() -> AsyncIterator[bytes]:
            cursor = after
            while True:
                page = await asyncio.to_thread(service.event_page, principal, task_id, cursor, 200)
                for event in page.events:
                    yield (
                        f"id: {event.sequence}\ndata: {event.model_dump_json()}\n\n"
                    ).encode("utf-8")
                    cursor = event.sequence
                task = await asyncio.to_thread(service.get_task, principal, task_id)
                if task.status in {"completed", "failed"} and not page.events:
                    break
                await asyncio.sleep(0.25)

        return StreamingResponse(generator(), media_type="text/event-stream")

    return app


def request_app(request: Request) -> Any:
    """Return the shared resource state attached to a request."""
    return request.app.state


def run() -> None:
    """Run the API process with uvicorn."""
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        create_app(settings),
        host="127.0.0.1",
        port=8100,
        log_level="info",
    )
