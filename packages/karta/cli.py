"""Command-line client for the kartā control plane.

The CLI is an API client only; it contains no agent implementation and never
connects to Pi, Marga, PostgreSQL or Redis directly.
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import click
import httpx

from .config import load_settings


@contextmanager
def api_client() -> Iterator[httpx.Client]:
    """Yield an authenticated HTTP client for the control plane."""
    settings = load_settings()
    if not settings.api_token:
        raise click.ClickException("KARTA_API_TOKEN is not set")
    headers = {"Authorization": f"Bearer {settings.api_token}"}
    with httpx.Client(base_url=settings.api_base_url, headers=headers, timeout=30.0) as client:
        yield client


def _raise_for_status(response: httpx.Response) -> None:
    """Convert API errors into readable CLI errors."""
    if response.status_code < 400:
        return
    try:
        detail = response.json().get("error", {}).get("message", response.text)
    except ValueError:
        detail = response.text
    raise click.ClickException(f"API error {response.status_code}: {detail}")


@click.group()
@click.version_option(package_name="karta")
def main() -> None:
    """kartā (कर्ता) — self-hostable agent platform CLI."""


@main.command()
def init() -> None:
    """Create local configuration and data directories."""
    settings = load_settings()
    config_dir = Path.home() / ".config" / "karta"
    config_dir.mkdir(parents=True, exist_ok=True)
    settings.projects_root.mkdir(parents=True, exist_ok=True)
    click.echo(f"Configuration directory: {config_dir}")
    click.echo(f"Projects directory: {settings.projects_root}")
    click.echo("Set KARTA_API_TOKEN before using API commands.")


@main.command()
def status() -> None:
    """Report API health and readiness."""
    settings = load_settings()
    with httpx.Client(base_url=settings.api_base_url, timeout=5.0) as client:
        for path in ("/health", "/ready"):
            response = client.get(path)
            click.echo(f"{path}: {response.status_code} {response.text.strip()}")


@main.group()
def project() -> None:
    """Manage local projects."""


@project.command(name="create")
@click.argument("name")
@click.option(
    "--workspace",
    "workspace_path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
)
def project_create(name: str, workspace_path: str) -> None:
    """Register an existing local workspace as a project."""
    with api_client() as client:
        response = client.post(
            "/api/v1/projects", json={"name": name, "workspace_path": workspace_path}
        )
    _raise_for_status(response)
    click.echo(json.dumps(response.json(), indent=2))


@project.command(name="list")
def project_list() -> None:
    """List projects visible to the authenticated tenant."""
    with api_client() as client:
        response = client.get("/api/v1/projects")
    _raise_for_status(response)
    click.echo(json.dumps(response.json(), indent=2))


@main.group()
def profile() -> None:
    """Inspect agent profiles."""


@profile.command(name="list")
def profile_list() -> None:
    """List stored agent profiles."""
    with api_client() as client:
        response = client.get("/api/v1/profiles")
    _raise_for_status(response)
    click.echo(json.dumps(response.json(), indent=2))


@main.group()
def task() -> None:
    """Create and inspect coding tasks."""


@task.command(name="run")
@click.argument("prompt")
@click.option("--project", "project_name", required=True, help="Registered project name.")
@click.option("--agent", "agent_id", default="coding", show_default=True)
@click.option("--version", "agent_version", default="1.0.0", show_default=True)
@click.option("--idempotency-key", default=None)
@click.option("--timeout", default=600.0, show_default=True, type=float)
@click.option("--json", "as_json", is_flag=True, help="Emit one JSON document.")
def task_run(
    prompt: str,
    project_name: str,
    agent_id: str,
    agent_version: str,
    idempotency_key: str | None,
    timeout: float,
    as_json: bool,
) -> None:
    """Run a coding task and wait for its final result."""
    with api_client() as client:
        projects = client.get("/api/v1/projects")
        _raise_for_status(projects)
        match = next(
            (item for item in projects.json()["projects"] if item["name"] == project_name),
            None,
        )
        if match is None:
            raise click.ClickException(f"Unknown project: {project_name}")
        payload: dict[str, Any] = {
            "prompt": prompt,
            "project_id": match["id"],
            "agent_profile_id": agent_id,
            "agent_profile_version": agent_version,
        }
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        created = client.post("/api/v1/tasks", json=payload)
        _raise_for_status(created)
        task_id = created.json()["id"]
        deadline = time.monotonic() + timeout
        while True:
            current = client.get(f"/api/v1/tasks/{task_id}")
            _raise_for_status(current)
            body = current.json()
            if body["status"] in {"completed", "failed"}:
                if as_json:
                    click.echo(json.dumps(body, indent=2))
                else:
                    click.echo(body.get("result") or body.get("error") or body["status"])
                if body["status"] == "failed":
                    sys.exit(1)
                return
            if time.monotonic() > deadline:
                raise click.ClickException(f"Task {task_id} did not finish before timeout")
            time.sleep(0.5)


@task.command(name="list")
def task_list() -> None:
    """List tasks for the authenticated tenant."""
    with api_client() as client:
        response = client.get("/api/v1/tasks")
    _raise_for_status(response)
    click.echo(json.dumps(response.json(), indent=2))


@task.command(name="show")
@click.argument("task_id")
def task_show(task_id: str) -> None:
    """Show one task."""
    with api_client() as client:
        response = client.get(f"/api/v1/tasks/{task_id}")
    _raise_for_status(response)
    click.echo(json.dumps(response.json(), indent=2))


@task.command(name="events")
@click.argument("task_id")
@click.option("--after", default=0, show_default=True, type=int)
def task_events(task_id: str, after: int) -> None:
    """Print a page of task events."""
    with api_client() as client:
        response = client.get(f"/api/v1/tasks/{task_id}/events", params={"after": after})
    _raise_for_status(response)
    click.echo(json.dumps(response.json(), indent=2))
