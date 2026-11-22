"""Unit tests for configuration, event schema and profile validation."""

from __future__ import annotations

import pytest
from karta.config import load_settings
from karta.events import AgentEvent, EventType
from karta.profiles import load_profiles
from pydantic import ValidationError

REQUIRED_ENV = {
    "KARTA_DATABASE_URL": "sqlite:///:memory:",
    "KARTA_API_TOKEN": "token",
}


def test_load_settings_rejects_blank_values() -> None:
    """Blank required configuration must fail fast."""
    with pytest.raises(ValueError, match="tenant_id"):
        load_settings({**REQUIRED_ENV, "KARTA_TENANT_ID": "  "})


def test_load_settings_rejects_unknown_queue_backend() -> None:
    """Only documented queue backends are accepted."""
    with pytest.raises(ValueError, match="KARTA_QUEUE_BACKEND"):
        load_settings({**REQUIRED_ENV, "KARTA_QUEUE_BACKEND": "kafka"})


def test_load_settings_strips_trailing_slashes() -> None:
    """Service URLs are normalized before use."""
    settings = load_settings({**REQUIRED_ENV, "KARTA_MARGA_URL": "http://127.0.0.1:8010/v1///"})
    assert settings.marga_base_url == "http://127.0.0.1:8010/v1"


def test_agent_event_requires_positive_sequence_and_tenant() -> None:
    """Event schema enforces the documented contract."""
    with pytest.raises(ValidationError):
        AgentEvent(
            tenant_id="",
            task_id="task-1",
            session_id="task-1",
            sequence=0,
            event_type=EventType.TASK_CREATED,
        )


def test_coding_profile_is_valid_and_stable() -> None:
    """The shipped coding profile validates and hashes deterministically."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "agent-profiles"
    profiles = load_profiles(root)
    assert set(profiles) == {"coding"}
    profile = profiles["coding"]
    assert profile.id == "coding"
    assert profile.version == "1.0.0"
    assert profile.runtime.engine == "pi"
    assert profile.limits.max_iterations == 35
    assert profile.content_hash() == profile.content_hash()
