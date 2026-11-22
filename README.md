# kartā (कर्ता)

**kartā** — Sanskrit कर्ता, "the doer" or "the agent" — is a self-hostable,
white-label agent platform for coding, research, automation, data analysis and
orchestration.

Pi executes. Marga supplies context, policy and model routing. OpenLIT observes.
The control plane governs identity, tasks, permissions, budgets and tenants.

**Status: Milestone 1 complete.** The Python control plane, TypeScript Pi
runtime, local Compose profile, tenant-scoped task API and basic coding profile
are implemented and tested. A CLI/API request runs a coding task against a
local test repository. See `docs/development/milestone-1.md` for the milestone
report and reproduction steps. Licensed under MIT; see `LICENSE`.

## Naming

| Use | Value |
|---|---|
| Display name | kartā |
| Devanagari wordmark | कर्ता |
| Repository, binary, Python distribution and module | `karta` |
| Config directory | `~/.config/karta/` |
| Data directory | `~/.local/share/karta/` |
| Environment prefix | `KARTA_` |
| Vault context | `karta` |

The upstream architecture document uses the placeholder name "Agent OS". Where
it says "Agent OS", read "kartā". See `requirements/adoption.md`.

## Source of truth

- `requirements/new-architecture.md` — adopted architecture specification,
  imported verbatim from `sutracoder` and not yet edited.
- `requirements/adoption.md` — name mapping and decisions already taken.
- `requirements/recursive-learn.md` — the schema-1 interaction contract that
  must survive via an event consumer (ADR-012).
- `docs/architecture/decisions/` — architecture decision records.
- `docs/architecture/open-questions.md` — inputs required from the maintainer.
- `docs/architecture/dependency-pins.md` — exact pinned versions and hashes.
- `docs/architecture/milestone-0-spike-results.md` — verified spike evidence.
- `docs/api/http-api.md` — control-plane and internal runtime HTTP contracts.
- `docs/api/events.md` — normalized `AgentEvent` schema and replay rules.
- `docs/development/milestone-1.md` — Milestone 1 report and reproduction steps.

## Repository map

```text
apps/runtime/          TypeScript Pi runtime adapter and HTTP service
packages/karta/        Python control plane: API, worker, CLI, persistence
agent-profiles/        declarative, versioned agent profiles
infrastructure/docker/ pinned Dockerfiles for the API and runtime images
compose*.yaml          local, dev, server and GPU overlay profiles
migrations/versions/   initial tenant-scoped SQL schema
tests/                 unit, integration, security, tenant-isolation, e2e
spikes/                pinned compatibility experiment (Milestone 0)
docs/                  architecture, api, deployment, security, development
requirements/          adopted specifications
```

Empty directories carry `.gitkeep`. They mark planned boundaries, not
implemented components.

## Quick start (Milestone 1)

Copy the template and fill in local tokens and a database password (never
commit real values):

```sh
cp .env.example .env
uv sync --frozen
cd apps/runtime && npm ci && cd ../..
docker compose -f compose.yaml -f compose.local.yaml up --build -d
uv run karta status
uv run karta project create test-repo --workspace /path/to/local/repo
uv run karta task run "Add a note to the repository" --project test-repo --json
```

The API binds `127.0.0.1:8100`, the runtime `127.0.0.1:8101`. Marga is a
separately versioned external service and is not started by this Compose
profile; kartā calls its OpenAI-compatible endpoint only.

A fully reproducible verification that needs no external model is available:

```sh
uv run python tests/e2e/verify_milestone_1.py
```

## Current milestone

**Milestone 1 — control plane and runtime foundation.** Exit criteria, from the
spec: a CLI/API request runs a coding task against a local test repository.
The CLI creates a durable task, a worker sends it to the TypeScript Pi runtime
over the documented HTTP contract, Pi calls workspace-scoped tools through
Marga, and ordered events plus the final result are persisted tenant-scoped.
The verification above exercises the real API, CLI and Pi runtime with a mock
Marga; see `docs/development/milestone-1.md` for results and known gaps.

Do not begin the web UI, full tenancy, sandbox or billing work ahead of their
milestones. Remaining maintainer inputs are tracked in
`docs/architecture/open-questions.md`.

## Related repositories

- `~/codebox/marga` — the gateway. Separately versioned. Has uncommitted local
  work; do not modify without explicit instruction.
- `~/codebox/sutracoder` — frozen at tag `sutracoder-v1-final`. Reference only;
  it is not shipped and receives no further changes.
