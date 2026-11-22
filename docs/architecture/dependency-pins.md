# Dependency pins

Versions were selected from upstream metadata on 2026-11-21, then verified
against the published package artifacts. They are not floating tags. Milestone 0
pins record the compatibility spike; Milestone 1 pins add the platform runtime
and deployment foundation.

## Pi runtime

| Package | Version | Integrity (npm) | Source |
|---|---|---|---|
| `@earendil-works/pi-agent-core` | 1.6.0 | `sha512-IU/x+2XtE4KIdIkEndZssdLPbIUR38Btj+Q7vjIIXIK7GSamLtDH5jOw/dzBWAvWFAgZ2dslF5sPc6GcGOnS+w==` | upstream tag `v1.6.0` |
| `@earendil-works/pi-ai` | 1.6.0 | `sha512-9hL+eygFDEiFp//cydeUfmFsKmEqpmvsNPb10Y1W8+m5K9O+sx1hMStfu6nukrBD5sl6mP4RykCYBBNEgsVLfw==` | upstream tag `v1.6.0` |
| `@earendil-works/pi-coding-agent` | 1.6.0 | `sha512-zX1BVEsshx7A2MRuQ6jfr3RJGWw4Wn+vLq5ZfmlvS1RskhRmByaSZVXH/zcwRrWHO7qPgs98pNCbPOEti/t0fQ==` | upstream tag `v1.6.0` |

- Upstream repository: `https://github.com/earendil-works/pi` (redirect target of
  the `badlogic/pi-mono` link in the architecture spec).
- Tag `v1.6.0` points to commit
  `faac585884ae2c013a6b1400f3e9e77f10b34bac` (2026-11-20).
- Licence: MIT.
- The spike uses `pi-agent-core` for the loop and `pi-ai` for the model adapter.
  `pi-coding-agent` is pinned for the later CLI/runtime work but is not loaded by
  the spike.

## OpenLIT

The `openlit-2.2.0` repository tag is a **monorepo release tag**; the published
SDK versions are different and are pinned separately.

| SDK | Version | Artifact hash | Source tag |
|---|---|---|---|
| Python `openlit` | 1.45.0 | wheel `sha256:9616c3210410649403280b6fbae770c11add04a776136db7ef2c60634821c25e` | `openlit-2.2.0` |
| TypeScript `openlit` | 1.15.0 | `sha512-cKBoGJLHG1OKlaD2yBVbJA4XkFK5s4sGPmJoOsLhSK8kUXalzdQD3Xi7e9eINys7PRArM2I9CaEnNcByKSwJsQ==` | `openlit-2.2.0` |

- Upstream repository: `https://github.com/openlit/openlit`.
- Tag `openlit-2.2.0` points to commit
  `463a1c1b3cd72a94fab4155efe0f28d90d87fe95` (2026-11-19).
- Licence: Apache-2.0 (Python SDK); the TypeScript package declares ISC in its
  `package.json` while the repository is Apache-2.0. `THIRD_PARTY_NOTICES.md`
  records both declarations.
- Installation method: exact versions in `spikes/milestone-0/pyproject.toml`
  (uv-managed) and `spikes/milestone-0/pi-runtime/package.json` (npm with a
  committed lockfile). No floating `latest` tags.

## Marga baseline used by the spike

The spike imports the existing local Marga tree read-only. It does not edit,
reset or commit that tree.

- Path: `~/codebox/marga`
- Branch: `main`
- HEAD: `21f305b Phase 6 final: Ruth memory update + dependency fix`
- Version: `0.2.0`
- The maintainer deferred bangtag work, so no bangtag/context-profile behaviour
  is exercised in this milestone.

## Milestone 1 platform pins

The control plane uses exact versions in `pyproject.toml` resolved through
`uv.lock`. Runtime tooling is exact in `apps/runtime/package.json` with a
committed `package-lock.json`. No `latest` tag is used anywhere.

### Python control plane

| Package | Version |
|---|---|
| fastapi | 0.165.0 |
| uvicorn | 0.54.0 |
| pydantic | 2.14.4 |
| sqlalchemy | 2.1.9 |
| psycopg | 3.3.9 |
| redis | 8.1.0 |
| httpx | 0.28.1 |
| pyyaml | 6.0.4 |
| click | 8.5.1 |
| pytest (dev) | 9.2.0 |
| ruff (dev) | 0.17.6 |
| hatchling (build backend) | 1.28.0 |

### TypeScript runtime tooling

| Package | Version |
|---|---|
| typescript | 5.9.3 |
| tsx | 4.23.15 |
| @types/node | 22.19.19 |
| @earendil-works/pi-agent-core | 1.6.0 |
| @earendil-works/pi-ai | 1.6.0 |

### Container images

| Image | Version | Verified |
|---|---|---|
| postgres | 17.6-alpine | manifest inspected |
| redis | 8.0.3-alpine | manifest inspected |
| python | 3.12.12-slim | manifest inspected |
| node | 22.19.0-alpine | manifest inspected |
| ghcr.io/astral-sh/uv | 0.10.7 | manifest inspected |

All Compose services use `network_mode: host` and bind only `127.0.0.1`.
Ports are `8100` (API), `8101` (runtime), `55432` (PostgreSQL) and `56379`
(Redis). Marga remains on its existing `8010` listener and is not started by
the kartā Compose profile.
