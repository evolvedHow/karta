"""Loading, validation and content hashing of declarative agent profiles."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from .errors import ApiError


class ProfileLimits(BaseModel):
    """Execution ceilings that a task must not exceed."""

    max_iterations: int = Field(ge=1, le=500)
    max_tool_calls: int = Field(ge=1, le=1000)
    max_execution_minutes: int = Field(ge=1, le=1440)


class ModelPolicy(BaseModel):
    """Marga model aliases referenced by a profile."""

    strong: str = Field(min_length=1)
    economical_coding: str | None = None


class RuntimeSpec(BaseModel):
    """Runtime engine used to execute the profile."""

    engine: Literal["pi"] = "pi"


class CodingProfile(BaseModel):
    """Validated, versioned basic coding agent profile."""

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = ""
    runtime: RuntimeSpec = Field(default_factory=RuntimeSpec)
    model_policy: ModelPolicy
    tools: list[str] = Field(default_factory=list)
    instructions: str = ""
    permissions: dict[str, str] = Field(default_factory=dict)
    limits: ProfileLimits

    def definition(self) -> dict[str, Any]:
        """Return the canonical JSON-ready profile definition."""
        return self.model_dump(mode="json")

    def content_hash(self) -> str:
        """Return a stable SHA-256 hash of the canonical definition."""
        payload = json.dumps(self.definition(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_profile(path: Path) -> CodingProfile:
    """Load and validate one ``profile.yaml`` file.

    Args:
        path: Path to the profile YAML document.

    Returns:
        Validated coding profile.

    Raises:
        ApiError: When the file is unreadable or invalid.

    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ApiError(500, "profile_unreadable", f"Cannot read profile at {path.name}") from exc
    try:
        return CodingProfile.model_validate(raw)
    except ValueError as exc:
        raise ApiError(500, "profile_invalid", f"Invalid profile at {path.name}: {exc}") from exc


def load_profiles(profiles_root: Path) -> dict[str, CodingProfile]:
    """Load every profile found under ``profiles_root``.

    Args:
        profiles_root: Directory containing one subfolder per profile.

    Returns:
        Mapping keyed by ``profile.id``.

    Raises:
        ApiError: When a duplicate profile identifier is found.

    """
    profiles: dict[str, CodingProfile] = {}
    if not profiles_root.is_dir():
        return profiles
    for candidate in sorted(profiles_root.glob("*/profile.yaml")):
        profile = load_profile(candidate)
        if profile.id in profiles:
            raise ApiError(500, "profile_duplicate", f"Duplicate profile identifier: {profile.id}")
        profiles[profile.id] = profile
    return profiles
