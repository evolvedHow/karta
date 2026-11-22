#!/usr/bin/env python3
"""Reproducible Milestone 1 exit-criteria check.

A CLI request runs a coding task against a local test repository. The script
starts three loopback-only processes with deterministic settings:

1. a mock Marga exposing the OpenAI-compatible wire format,
2. the real TypeScript Pi runtime, and
3. the real FastAPI control plane with an embedded worker.

It then registers a temporary repository, runs ``karta task run`` against it,
and asserts that the task completed, the tool call changed a file, and the
durable event log contains the expected ordered sequence. No real provider
credential or external model is involved.

Run from the repository root::

    uv run python tests/e2e/verify_milestone_1.py
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
MOCK_PORT = 8092
RUNTIME_PORT = 8101
API_PORT = 8100
API_TOKEN = "e2e-api-token"
INTERNAL_TOKEN = "e2e-internal-token"
NOTE_NAME = "note.txt"
NOTE_CONTENT = "hello kartā"


class ManagedProcess:
    """A subprocess whose process group is terminated on cleanup."""

    def __init__(self, name: str, command: list[str], env: dict[str, str], cwd: Path) -> None:
        """Start the process with its own session.

        Args:
            name: Human-readable process name for diagnostics.
            command: Executable and arguments.
            env: Complete environment for the child.
            cwd: Working directory for the child.

        """
        self.name = name
        self.log_path = REPO_ROOT / ".local" / f"e2e-{name}.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = self.log_path.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=self._log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    def alive(self) -> bool:
        """Return whether the process is still running."""
        return self.process.poll() is None

    def stop(self) -> None:
        """Terminate the whole process group, escalating to kill if needed."""
        if not self.alive():
            self._log.close()
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.process.wait(timeout=10)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait(timeout=10)
        finally:
            self._log.close()

    def tail(self, lines: int = 30) -> str:
        """Return the last log lines for diagnostics."""
        return "\n".join(self.log_path.read_text(encoding="utf-8").splitlines()[-lines:])


def wait_ready(url: str, processes: list[ManagedProcess], timeout: float = 30.0) -> None:
    """Poll a health endpoint until it succeeds.

    Args:
        url: Health endpoint URL.
        processes: Processes to include in failure diagnostics.
        timeout: Maximum wait in seconds.

    Raises:
        RuntimeError: When the endpoint does not become healthy in time.

    """
    deadline = time.monotonic() + timeout
    last_error = "no response"
    with httpx.Client(timeout=1.0) as client:
        while time.monotonic() < deadline:
            try:
                response = client.get(url)
                if response.status_code == 200:
                    return
                last_error = f"HTTP {response.status_code}"
            except httpx.HTTPError as exc:
                last_error = str(exc)
            if any(not process.alive() for process in processes):
                break
            time.sleep(0.25)
    details = "\n".join(f"{p.name}:\n{p.tail()}" for p in processes)
    raise RuntimeError(f"{url} did not become ready ({last_error}).\n{details}")


def run_cli(env: dict[str, str], *arguments: str) -> str:
    """Run one CLI command against the live API.

    Args:
        env: Environment containing the API token and URL.
        *arguments: CLI arguments after ``karta``.

    Returns:
        Standard output of the command.

    Raises:
        RuntimeError: When the command exits non-zero.

    """
    venv_bin = Path(sys.executable).parent
    result = subprocess.run(
        [str(venv_bin / "karta"), *arguments],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"karta {' '.join(arguments)} failed ({result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result.stdout


def main() -> int:
    """Run the full verification and print a compact JSON summary.

    Returns:
        ``0`` when every exit criterion is satisfied, ``1`` otherwise.

    """
    temporary = Path(tempfile.mkdtemp(prefix="karta-m1-e2e-"))
    workspace = temporary / "test-repo"
    workspace.mkdir()
    (workspace / "README.md").write_text("initial\n", encoding="utf-8")

    base_env = dict(os.environ)
    base_env.update(
        {
            "KARTA_API_TOKEN": API_TOKEN,
            "KARTA_INTERNAL_TOKEN": INTERNAL_TOKEN,
            "KARTA_TENANT_ID": "e2e-tenant",
            "KARTA_QUEUE_BACKEND": "memory",
            "KARTA_EMBED_WORKER": "1",
            "KARTA_DATABASE_URL": f"sqlite:///{temporary / 'karta.db'}",
            "KARTA_MARGA_URL": f"http://127.0.0.1:{MOCK_PORT}/v1",
            "KARTA_MARGA_API_KEY": "mock-provider-key",
            "KARTA_RUNTIME_URL": f"http://127.0.0.1:{RUNTIME_PORT}",
            "KARTA_API_URL": f"http://127.0.0.1:{API_PORT}",
            "KARTA_PROJECTS_ROOT": str(temporary / "projects"),
        }
    )
    runtime_env = dict(base_env)
    runtime_env["KARTA_RUNTIME_PORT"] = str(RUNTIME_PORT)

    venv_bin = Path(sys.executable).parent
    processes: list[ManagedProcess] = []
    try:
        processes.append(
            ManagedProcess(
                "marga",
                [sys.executable, "tests/e2e/mock_marga.py", "--port", str(MOCK_PORT)],
                base_env,
                REPO_ROOT,
            )
        )
        processes.append(
            ManagedProcess(
                "runtime",
                ["npm", "run", "start"],
                runtime_env,
                REPO_ROOT / "apps" / "runtime",
            )
        )
        wait_ready(f"http://127.0.0.1:{MOCK_PORT}/health", processes)
        wait_ready(f"http://127.0.0.1:{RUNTIME_PORT}/health", processes)

        processes.append(
            ManagedProcess("api", [str(venv_bin / "karta-api")], base_env, REPO_ROOT)
        )
        wait_ready(f"http://127.0.0.1:{API_PORT}/health", processes)

        project_output = run_cli(
            base_env,
            "project",
            "create",
            "test-repo",
            "--workspace",
            str(workspace),
        )
        project_id = json.loads(project_output)["id"]
        task_output = run_cli(
            base_env,
            "task",
            "run",
            "Write the note file and report what you changed.",
            "--project",
            "test-repo",
            "--json",
        )
        task = json.loads(task_output)
        task_id = str(task["id"])

        if task["status"] != "completed":
            raise RuntimeError(f"Task {task_id} is {task['status']}: {task.get('error')}")

        written = (workspace / NOTE_NAME).read_text(encoding="utf-8")
        assert written == NOTE_CONTENT, f"unexpected file content: {written!r}"

        with httpx.Client(
            base_url=f"http://127.0.0.1:{API_PORT}",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=10.0,
        ) as client:
            event_page = client.get(f"/api/v1/tasks/{task_id}/events").json()
        events = event_page["events"]
        types = [event["event_type"] for event in events]
        for required in ("task.created", "task.started", "tool.completed", "task.completed"):
            assert required in types, f"missing event {required}: {types}"
        assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
        assert all(event["correlation_id"] for event in events)
        assert all(event["tenant_id"] == "e2e-tenant" for event in events)

        summary: dict[str, Any] = {
            "status": "pass",
            "project_id": project_id,
            "task_id": task_id,
            "status_value": task["status"],
            "final_text": task["result"],
            "file": NOTE_NAME,
            "file_content": written,
            "event_count": len(events),
            "event_types": types,
            "test_repository": str(workspace),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    finally:
        for process in reversed(processes):
            process.stop()
        shutil.rmtree(temporary, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
