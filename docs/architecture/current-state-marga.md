# Current state of Marga

Status: inventory completed 2026-11-21 against the local checkout.
Repo: `~/codebox/marga`. Integration boundary: `services/marga/`.

This document satisfies the first Milestone 0 deliverable required by §27 of the
architecture specification. It describes the code as it exists on disk, not as
the README or comparison documents describe it.

## Provenance and working tree

| Item | Observed |
|---|---|
| Branch | `main` |
| HEAD | `21f305b Phase 6 final: Ruth memory update + dependency fix` |
| Package version | `0.2.0` (`marga/_version.py`) |
| Distribution | `marga`, Python ≥3.11, FastAPI + httpx + uvicorn + Pydantic v2 |
| Licence | Apache-2.0 (`LICENSE`), `NOTICE` credits Vish Ganapathy, 2026 |
| Working tree | Dirty: modified `Dockerfile`, `docker-compose.yml`, `marga/models.py`, `marga/proxy.py`; untracked `marga.toml` |

The uncommitted work was left untouched. It must be reconciled with the
maintainer before any kartā work assumes a gateway baseline.

## Size and modules

The `marga/` package is **4,233 lines across 17 Python modules**, plus
`worker.py` for the Cloudflare Workers deployment and one test file.

| Module | Lines | Role |
|---|---:|---|
| `proxy.py` | 795 | FastAPI app construction and request handling |
| `router.py` | 413 | Backend selection and routing table |
| `strategies.py` | 366 | `least_used`, `round_robin`, `cheapest`, `budget` |
| `vault.py` | 355 | worker-env secret resolution |
| `anthropic.py` | 291 | Anthropic `/v1/messages` translation |
| `hooks.py` | 274 | Before/after hook system |
| `transport.py` | 238 | httpx request forwarding, streaming and non-streaming |
| `models.py` | 306 | Pydantic wire models |
| `store.py` | 195 | Pluggable usage counters (in-memory default, pluggable store seam) |
| `errors.py` | 162 | `MargaError` exception hierarchy |
| `availability.py` | 139 | Backend probing with local/cloud runtime detection |
| `config.py` | 134 | TOML configuration loading |
| `cli.py` | 123 | `marga serve` command |
| `_util.py` | 119 | Shared helpers |
| `middleware.py` | 145 | Request middleware |
| `__init__.py` | 29 | Public exports |
| `_version.py` | 11 | Single source of version truth |

## HTTP surface

Verified in `marga/proxy.py`:

- `GET /` — proxy metadata
- `GET /health` — liveness, version, runtime and per-backend reachability
- `GET /stats` — per-backend call, token and cost counters; window `all|month|day`
- `GET /v1/models` — models exposed by the routing table, IDs qualified as
  `backend/model`
- `POST /v1/chat/completions` — OpenAI-compatible, SSE stream when
  `stream=true`
- `POST /v1/messages` — Anthropic-compatible, translated to the OpenAI shape

Gateway authentication is a single optional bearer token (`MARGA_AUTH_TOKEN`),
accepted as `Authorization: Bearer` or `x-api-key`. `/health` and `/docs` are
public. CORS origins are configurable.

## Tests

`tests/test_marga.py` contains **7 test functions** in a single file. That is
not sufficient coverage for a gateway kartā intends to make a first-class
platform component.

## Documentation drift

`COMPARISON.md` and `TRANSFORMATION.md` describe a 509-line, five-file minimal
library created by reducing a 10,389-line "margAI" framework. Those figures are
historical: the code on disk is 4,233 lines across 17 modules and has continued
evolving through at least Phase 6. Treat those documents as a record of what was
*removed from margAI*, not as a description of the current gateway.

The architecture spec's §1.2 describes Marga as "a deliberately slim"
proxy. That description matches the historical documents, not this checkout.
This discrepancy is a decision for the maintainer.

## Capability gap against the kartā specification

Verified absent from the Python source (no matches for `bangtag`, `virtual
model`, `tenant`, `context profile`, `trace_id`, OpenTelemetry or OpenLIT):

- Bangtag parsing, escaping, precedence and profile access control (§5.3).
- Context profile resolution, versioning and content hashing (§5.4).
- Virtual model aliases and capability-based routing (§5.5, §5.6).
- Signed tenant/task context, tenant isolation and admin-scoped endpoints (§5.1,
  §5.9, §5.10).
- Durable, append-only usage ledger; current accounting is counter-based with a
  pluggable store seam (§9.4, §5.8).
- Correlation IDs, trace propagation and OpenLIT instrumentation (§9).
- Provider error normalisation into the specified categories; an internal
  `MargaError` hierarchy exists but does not cover the spec's taxonomy (§5.7).
- Streaming usage accounting, response hooks, partial/aborted call recording and
  client-disconnect cancellation need verification against the actual stream
  path before any claim is made (§5.8).
- Request size limits, rate limits by tenant, SSRF egress restrictions and
  constant-time secret comparison (§5.10).

## Consequences for Milestone 0

1. Do not assume the slim-code baseline from §1.2. Establish which tree is
   authoritative before designing extensions.
2. The hooks system and pluggable `UsageStore` are the most promising existing
   seams for context infusion and a durable usage ledger. Validate rather than
   replace them.
3. The Anthropic compatibility surface is extra scope not required by kartā's
   §5.9; keep it working, but do not let it drive gateway policy design.
4. No gateway changes are made from this repository. Changes belong in
   `~/codebox/marga` and require the maintainer's decision on its dirty tree.
