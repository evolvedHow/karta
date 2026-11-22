"""Worker loop that delivers queued tasks to the execution service."""

from __future__ import annotations

import logging
import signal
import threading
from typing import Protocol

from .config import Settings, load_settings
from .db import create_db_engine, run_migrations
from .queue import InMemoryTaskQueue, RedisTaskQueue, TaskQueue
from .runtime_client import RuntimeClient
from .tasks import TaskService

LOGGER = logging.getLogger("karta.worker")


class StopSignal(Protocol):
    """Minimal interface shared by ``asyncio.Event`` and ``threading.Event``."""

    def is_set(self) -> bool:
        """Return whether shutdown was requested."""
        ...


def run_worker_loop(service: TaskService, queue: TaskQueue, stop: StopSignal) -> None:
    """Consume queue messages until ``stop`` is set.

    Args:
        service: Application service used to execute tasks.
        queue: Queue implementing :class:`~karta.queue.TaskQueue`.
        stop: Event signalling graceful shutdown.

    """
    while not stop.is_set():
        message = queue.dequeue(timeout=0.5)
        if message is None:
            continue
        try:
            service.execute(message.tenant_id, message.task_id, message.correlation_id)
        except Exception:
            LOGGER.exception("Task execution failed for %s", message.task_id)
        finally:
            queue.ack(message)


def run() -> None:
    """Run the worker process until SIGINT or SIGTERM."""
    logging.basicConfig(level=logging.INFO)
    settings: Settings = load_settings()
    engine = create_db_engine(settings)
    run_migrations(engine, "migrations")
    queue: TaskQueue
    if settings.queue_backend == "memory":
        queue = InMemoryTaskQueue()
    else:
        queue = RedisTaskQueue.from_settings(settings)
    queue.recover()
    runtime = RuntimeClient(settings.runtime_url, settings.internal_token)
    service = TaskService(settings, engine, queue, runtime)
    stop = threading.Event()

    def handle_signal(signum: int, frame: object) -> None:
        """Request graceful shutdown on a termination signal."""
        stop.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    LOGGER.info("kartā worker started (tenant=%s)", settings.tenant_id)
    try:
        run_worker_loop(service, queue, stop)
    finally:
        queue.close()
        runtime.close()
        engine.dispose()
