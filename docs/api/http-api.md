# kartā HTTP API (Milestone 1)

Base URL: `http://127.0.0.1:8100`. OpenAPI JSON is served at `/openapi.json`
and interactive documentation at `/docs`. All request and response bodies are
JSON. Field names are `snake_case` across both language boundaries.

## Authentication

All `/api/v1/*` endpoints require `Authorization: Bearer <KARTA_API_TOKEN>`.
The token is compared in constant time. The authenticated principal supplies
the tenant identifier; clients cannot choose it by sending a `tenant_id` field
(a supplied field is ignored). `/health` and `/ready` are public.

Every response carries `X-Correlation-ID`. A caller may supply one with the
`X-Correlation-ID` request header; otherwise the API generates a UUID. Errors
use this envelope:

```json
{
  "error": {
    "code": "project_not_found",
    "message": "Project does not exist for this tenant",
    "details": {},
    "correlation_id": "b7e1..."
  }
}
```

## Operations

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | no | Process liveness. |
| `GET` | `/ready` | no | Database and queue readiness; `503` when unavailable. |
| `GET` | `/api/v1/projects` | `projects:read` | List tenant projects. |
| `POST` | `/api/v1/projects` | `projects:write` | Register an existing local workspace. `201`. |
| `GET` | `/api/v1/profiles` | `profiles:read` | List stored profile versions. |
| `POST` | `/api/v1/tasks` | `tasks:write` | Create and enqueue a task. `202`. |
| `GET` | `/api/v1/tasks` | `tasks:read` | List tenant tasks, newest first. |
| `GET` | `/api/v1/tasks/{task_id}` | `tasks:read` | Read one task. |
| `GET` | `/api/v1/tasks/{task_id}/events` | `tasks:read` | Page of events after `after` (default `0`), `limit` 1–1000. |
| `GET` | `/api/v1/tasks/{task_id}/events/stream` | `tasks:read` | SSE stream; resume with `Last-Event-ID`. |

### Create project

```json
{ "name": "test-repo", "workspace_path": "/home/user/repos/test-repo" }
```

The directory must already exist. Returns `ProjectRead`.

### Create task

```json
{
  "prompt": "Add a README section describing the build command",
  "project_id": "0f1b...",
  "agent_profile_id": "coding",
  "agent_profile_version": "1.0.0",
  "idempotency_key": "optional-stable-key"
}
```

A repeated `idempotency_key` for the same tenant returns the original task.
The response is `TaskRead` with `status: "queued"`.

### Task states

`queued` → `running` → `completed` | `failed`. `result` holds final assistant
text on success; `error` holds a sanitized description on failure.

### SSE framing

Each frame is an event sequence identifier followed by the full `AgentEvent`:

```text
id: 3
data: {"event_id":"...","tenant_id":"tenant-a","task_id":"...","sequence":3,...}

```

Reconnect by sending `Last-Event-ID: 3`; only later events are replayed. The
stream closes when the task reaches a terminal state.

## Internal control-plane to runtime API

This endpoint is not exposed to tenants. It requires
`X-Karta-Internal-Token: <KARTA_INTERNAL_TOKEN>` and is bound to
`127.0.0.1:8101`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Public runtime liveness. |
| `POST` | `/v1/execute` | Execute one task with the pinned Pi SDK. |

`ExecutionRequest` fields: `task_id`, `tenant_id`, `session_id`, `prompt`,
`workspace_path`, `profile`, `marga_base_url`, `model`, `api_key`,
`correlation_id`, `limits`. `ExecutionResult` fields: `task_id`, `status`,
`final_text`, `stop_reason`, `events`, `usage`, `error`. The full schema is
implemented in `packages/karta/models.py` and
`apps/runtime/src/contracts.ts`; tests on both sides validate it.

Marga's own OpenAI-compatible surface is documented in its repository. kartā
does not reimplement or proxy provider policy.
