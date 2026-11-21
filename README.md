# kartā (कर्ता)

**kartā** — Sanskrit कर्ता, "the doer" or "the agent" — is a self-hostable,
white-label agent platform for coding, research, automation, data analysis and
orchestration.

Pi executes. Marga supplies context, policy and model routing. OpenLIT observes.
The control plane governs identity, tasks, permissions, budgets and tenants.

**Status: Milestone 0 spike complete.** Dependency versions are pinned and the
Pi → Marga → model path has been verified with streaming, tool calling and
trace correlation. No platform application code or Compose deployment exists
yet. Licensed under MIT; see `LICENSE`.

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
- `docs/architecture/dependency-pins.md` — exact Milestone 0 versions and hashes.
- `docs/architecture/milestone-0-spike-results.md` — verified spike evidence.

## Repository map

```text
apps/            web (React), api (FastAPI), runtime (Pi/TypeScript), cli, worker
services/marga   integration surface for the separately versioned Marga service
packages/        shared contracts and platform modules named in §24 of the spec
agent-profiles/  declarative, versioned agent profiles
context-profiles/ versioned context packages
infrastructure/  docker, compose, postgres, redis, openlit, litellm, monitoring
migrations/      database migrations
tests/           unit, integration, security, tenant-isolation, evaluations, e2e
spikes/          pinned, isolated compatibility experiments (Milestone 0)
docs/            architecture, api, deployment, security, development
requirements/    adopted specifications
```

Empty directories carry `.gitkeep`. They mark planned boundaries, not
implemented components.

## Current milestone

**Milestone 0 — repository and compatibility spike.** Exit criteria, from the
spec: a minimal Pi → Marga → model call works end to end with streaming, tool
calling and trace correlation demonstrated. The three investigation documents
required by §27 are in `docs/architecture/`:

- `current-state-marga.md` — inventory completed against the local checkout.
- `pi-compatibility-spike.md` — procedure, executed.
- `openlit-instrumentation-spike.md` — procedure, executed.

The exit criteria are met; see `docs/architecture/milestone-0-spike-results.md`.
Do not begin the web UI or multi-tenant implementation beyond Milestone 1 until
the remaining maintainer inputs are resolved.

## Related repositories

- `~/codebox/marga` — the gateway. Separately versioned. Has uncommitted local
  work; do not modify without explicit instruction.
- `~/codebox/sutracoder` — frozen at tag `sutracoder-v1-final`. Reference only;
  it is not shipped and receives no further changes.
