# Milestone 1 report — control plane and runtime foundation

Status: **complete**, pending the maintainer inputs listed under Known gaps.

## Scope

From §24–§25 of the adopted specification: a monorepo with a local Compose
profile, PostgreSQL with migrations, Redis, a FastAPI health/auth skeleton, a
Pi runtime adapter, Marga as the policy gateway, one provider path and one
basic coding profile. Exit criteria: a CLI/API request runs a coding task
against a local test repository.

The implementation follows ADR-005: Python owns the control plane, TypeScript
owns the Pi runtime, and the two communicate only through the documented HTTP
and event contracts in `docs/api/`.

## Implemented components

| Area | Location | Notes |
|---|---|---|
| Configuration and errors | `packages/karta/config.py`, `errors.py` | Validated `KARTA_*` settings; blank required values fail fast. |
| Schema and migrations | `migrations/versions/0001_initial.sql`, `packages/karta/db.py` | Raw SQL with a checksum guard; tenant on every task row. |
| Auth | `packages/karta/auth.py` | Constant-time bearer token, explicit scopes; tenant always from the principal. |
| Persistence | `packages/karta/repository.py` | Every query takes `tenant_id`; monotonic event sequences. |
| Contracts | `packages/karta/models.py`, `events.py`, `apps/runtime/src/contracts.ts` | `ExecutionRequest`, `ExecutionResult`, `AgentEvent`; `snake_case` on both sides. |
| Profiles | `agent-profiles/coding/`, `packages/karta/profiles.py` | Versioned coding profile with content hash; `read_file`, `write_file`, `list_files`. |
| Queue and worker | `packages/karta/queue.py`, `worker.py` | In-memory queue and Redis queue with per-tenant lists and recovery. |
| Task service | `packages/karta/tasks.py` | Create/enqueue/execute/persist; idempotency; usage and terminal events. |
| API | `packages/karta/api.py` | Health, readiness, projects, profiles, tasks, paged events and SSE replay. |
| CLI | `packages/karta/cli.py` | API client only; `init`, `status`, `project`, `profile`, `task`. |
| Runtime | `apps/runtime/src/` | HTTP server, Pi adapter, workspace tools; internal-token auth. |
| Deployment | `compose*.yaml`, `infrastructure/docker/` | Pinned images, loop-only binds, healthchecks, dev/server overlays. |

## Commands run

```sh
uv sync --frozen
uv run ruff check .
uv run pytest -q
cd apps/runtime && npm ci && npm run typecheck && npm test && npm run build
cd ../.. && docker compose -f compose.yaml -f compose.local.yaml config --quiet
uv run python tests/e2e/verify_milestone_1.py
ss -tlnp | awk 'NR>1 {print $4}' | grep '^0\.0\.0\.0:'
```

## Test results

- Python: **21 passed** (`tests/unit`, `tests/integration`, `tests/security`,
  `tests/tenant-isolation`). Includes the release-blocker cross-tenant tests:
  tenant B cannot read tenant A's tasks, events or SSE stream, cannot use
  tenant A's project, and cannot see tenant A's pinned profile.
- TypeScript: **11 passed** (`apps/runtime/test`). Includes contract validation,
  workspace-traversal rejection, internal-token auth, and a real Pi agent loop
  that executes a `write_file` tool call against a mock Marga SSE endpoint.
- Ruff: all checks passed. TypeScript `tsc --noEmit` and `tsc -p
  tsconfig.build.json` both clean.
- Compose configuration validates for the base and local overlay.
- E2E exit-criteria check: **pass**. Output:

```json
{
  "status": "pass",
  "status_value": "completed",
  "final_text": "Wrote the note.",
  "file": "note.txt",
  "file_content": "hello kartā",
  "event_count": 10,
  "event_types": [
    "task.created", "task.started", "message.complete", "tool.started",
    "tool.completed", "message.delta", "message.delta", "message.complete",
    "usage.recorded", "task.completed"
  ]
}
```

- No socket is bound to `0.0.0.0`; the E2E loopback ports are released after
  the run.

## Changed files

New: `pyproject.toml`, `uv.lock`, `packages/karta/`, `migrations/`,
`agent-profiles/coding/`, `apps/runtime/`, `compose.yaml`, `compose.local.yaml`,
`compose.dev.yaml`, `compose.server.yaml`, `compose.gpu.yaml`,
`infrastructure/docker/`, `tests/`, `docs/api/`, ADR-005.
Modified: `.env.example`, `.gitignore`, `README.md`, `THIRD_PARTY_NOTICES.md`,
`docs/architecture/decisions/README.md`, `docs/architecture/dependency-pins.md`.

## Known gaps

- Marga is imported as an external baseline (ADR-002). The local checkout has
  uncommitted work and was not touched. The `strong` / `economical-coding`
  aliases in the coding profile are resolved by Marga in Milestone 2; this
  milestone used a mock Marga that echoes the requested model, so real alias
  resolution is not yet proven end to end.
- Local mode uses one bearer token and one tenant. Full OIDC, per-user tenants
  and PostgreSQL row-level security belong to Milestone 7. The single-tenant
  path is already tenant-scoped at every repository query.
- The worker executes synchronously per queue message. Durable recovery and
  crash semantics are Milestone 3 work; the Redis queue has basic in-flight
  recovery but no lease fencing.
- Tools are limited to workspace `read_file`, `write_file` and `list_files`.
  Terminal, git and network tools wait for the sandbox in Milestone 4.
- OpenLIT/OpenTelemetry instrumentation is planned for Milestone 5; events
  carry `trace_id: null` and `correlation_id` is the only linkage today.
- Bangtags and context profiles are deferred pending the maintainer's
  resolution of the margAI source (see `docs/architecture/open-questions.md`).
- Web UI, billing, additional profiles and server hardening are intentionally
  out of scope.

## Next milestone recommendation

Milestone 2 — context and bangtag handling, including profile resolution and
the documented event consumer that derives the schema-1 record. Do not start
it until the maintainer supplies the authoritative margAI/bangtag source and
confirms Marga alias resolution for `strong` and `economical-coding`.
