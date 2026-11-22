"""Tenant-aware durable task queue with an in-memory implementation for tests."""

from __future__ import annotations

import json
import queue
from dataclasses import dataclass
from typing import Protocol

import redis

from .config import Settings


@dataclass(frozen=True)
class TaskMessage:
    """One dequeueable task notification.

    Attributes:
        task_id: Durable task identifier in PostgreSQL/SQLite.
        tenant_id: Tenant that owns the task.
        correlation_id: Correlation identifier propagated across services.
        attempt: Number of delivery attempts so far.

    """

    task_id: str
    tenant_id: str
    correlation_id: str
    attempt: int = 1

    def to_json(self) -> str:
        """Serialize the message for queue transport."""
        return json.dumps(
            {
                "task_id": self.task_id,
                "tenant_id": self.tenant_id,
                "correlation_id": self.correlation_id,
                "attempt": self.attempt,
            },
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, value: str) -> TaskMessage:
        """Deserialize a message from queue transport."""
        raw = json.loads(value)
        return cls(
            task_id=raw["task_id"],
            tenant_id=raw["tenant_id"],
            correlation_id=raw["correlation_id"],
            attempt=int(raw.get("attempt", 1)),
        )


class TaskQueue(Protocol):
    """Contract implemented by both the Redis and in-memory queues."""

    def enqueue(self, message: TaskMessage) -> None:
        """Append a task notification."""
        ...

    def dequeue(self, timeout: float = 1.0) -> TaskMessage | None:
        """Block briefly and return the next notification, if any."""
        ...

    def ack(self, message: TaskMessage) -> None:
        """Mark a delivered notification as handled."""
        ...

    def recover(self) -> int:
        """Return in-flight notifications to their ready queues."""
        ...

    def close(self) -> None:
        """Release queue resources."""
        ...


class InMemoryTaskQueue:
    """Process-local queue used by tests and single-process development."""

    def __init__(self) -> None:
        """Initialise empty ready and in-flight collections."""
        self._ready: queue.Queue[TaskMessage] = queue.Queue()
        self._in_flight: list[TaskMessage] = []

    def enqueue(self, message: TaskMessage) -> None:
        """Append a task notification."""
        self._ready.put(message)

    def dequeue(self, timeout: float = 1.0) -> TaskMessage | None:
        """Return the next notification, waiting up to ``timeout`` seconds."""
        try:
            message = self._ready.get(timeout=timeout)
        except queue.Empty:
            return None
        self._in_flight.append(message)
        return message

    def ack(self, message: TaskMessage) -> None:
        """Remove a delivered notification from the in-flight list."""
        self._in_flight = [item for item in self._in_flight if item != message]

    def recover(self) -> int:
        """Return all in-flight notifications to the ready queue."""
        count = len(self._in_flight)
        for message in self._in_flight:
            self._ready.put(message)
        self._in_flight = []
        return count

    def close(self) -> None:
        """No resources to release."""
        return None


class RedisTaskQueue:
    """Redis-backed queue with per-tenant lists and in-flight recovery."""

    def __init__(self, client: redis.Redis, tenants: list[str]) -> None:
        """Initialise the queue.

        Args:
            client: Connected Redis client.
            tenants: Tenants whose queues the worker should poll.

        """
        self._client = client
        self._tenants = list(dict.fromkeys(tenants))

    @classmethod
    def from_settings(cls, settings: Settings) -> RedisTaskQueue:
        """Create a queue from validated settings."""
        return cls(redis.Redis.from_url(settings.redis_url), [settings.tenant_id])

    def _ready_key(self, tenant_id: str) -> str:
        return f"karta:tasks:{tenant_id}:ready"

    def _processing_key(self, tenant_id: str) -> str:
        return f"karta:tasks:{tenant_id}:processing"

    def enqueue(self, message: TaskMessage) -> None:
        """Append a task notification to its tenant-scoped ready list."""
        self._client.rpush(self._ready_key(message.tenant_id), message.to_json())

    def dequeue(self, timeout: float = 1.0) -> TaskMessage | None:
        """Atomically move one notification to its tenant processing list."""
        for tenant_id in self._tenants:
            raw = self._client.brpoplpush(
                self._ready_key(tenant_id),
                self._processing_key(tenant_id),
                timeout=max(0.1, timeout / max(1, len(self._tenants))),
            )
            if raw is not None:
                return TaskMessage.from_json(raw.decode("utf-8"))
        return None

    def ack(self, message: TaskMessage) -> None:
        """Remove a delivered notification from its processing list."""
        self._client.lrem(self._processing_key(message.tenant_id), 1, message.to_json())

    def recover(self) -> int:
        """Return all processing-list notifications to their ready lists."""
        recovered = 0
        for tenant_id in self._tenants:
            processing = self._processing_key(tenant_id)
            ready = self._ready_key(tenant_id)
            while True:
                raw = self._client.rpoplpush(processing, ready)
                if raw is None:
                    break
                recovered += 1
        return recovered

    def close(self) -> None:
        """Close the Redis client."""
        self._client.close()
