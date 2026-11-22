# ADR-005: Python control plane, TypeScript Pi runtime, documented HTTP boundary

Status: Accepted (Milestone 1).

## Context

The Pi SDK is TypeScript-only. The control plane is Python/FastAPI. Section 4.1
of the specification requires the two languages to communicate through
documented HTTP APIs and event schemas, never shared internal code. Milestone 0
proved the pinned Pi 1.6.0 SDK can stream, call tools and reach Marga through
its OpenAI-compatible surface.

## Decision

- `packages/karta/` is the Python control-plane module: configuration,
  migrations, tenant-scoped persistence, auth, task orchestration, queue,
  worker, FastAPI app and CLI. It is deployed as two processes (`api`, `worker`)
  from one image, which keeps the system a modular monolith.
- `apps/runtime/` is a separate TypeScript service embedding the Pi SDK. It
  exposes only `GET /health` and `POST /v1/execute`. Pi-specific types are
  confined to `adapter.ts` and `tools.ts`; the runtime emits only the
  documented `AgentEvent` JSON schema.
- The control plane sends `ExecutionRequest` to the runtime over loopback HTTP
  with an internal bearer token. The runtime never calls PostgreSQL, Redis,
  Marga's admin API or the control plane directly.
- Marga remains a separately versioned external service (ADR-002) and the sole
  routing/policy authority. kartā calls only its OpenAI-compatible endpoint;
  LiteLLM is out of scope (ADR-003).
- `task_events` is the authoritative ordered event log with
  `PRIMARY KEY (task_id, sequence)` and a `correlation_id` column. Redis is a
  delivery mechanism, never the record of task state. SSE replays from the
  database using `Last-Event-ID`.
- No schema-1 JSONL emitter exists in either process (ADR-012).

## Consequences

- A language-neutral contract must be versioned in `docs/api/`; both sides have
  tests that validate the same field names and types.
- The extra network hop is acceptable: both processes bind `127.0.0.1` and use
  `network_mode: host` in Compose so Marga on the host loopback stays reachable.
- Cross-tenant isolation is enforced at the API and repository layers. The
  runtime receives tenant identifiers only for event stamping; Marga receives
  task and correlation headers, never a tenant identity it could trust.
- Full OIDC, RLS, sandboxing, OpenLIT instrumentation and extra profiles remain
  later milestones.
