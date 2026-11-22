# Third-party notices

This file records attribution obligations for components kartā depends on or
evolves. It is not a complete software bill of materials; exact resolved
versions are recorded in the committed `uv.lock`, `apps/runtime/package-lock.json`
and `docs/architecture/dependency-pins.md`.

## Marga

- Project: marga — https://github.com/evolvedHow/marga
- Local checkout: `~/codebox/marga`, package version `0.2.0`
- Licence: Apache License 2.0
- Notice: "marga — Copyright 2026 Vish Ganapathy. This product includes software
  developed by Vish Ganapathy."

Marga is a separately versioned upstream. kartā does not copy it into this
repository. The Milestone 0 spike imports it read-only from its existing
checkout; no Marga source file was modified. If gateway code is modified as
part of kartā, the modified files must be identified here and the upstream
licence and notice preserved.

## Pi runtime (Milestone 0 pin)

- Project: earendil-works/pi — https://github.com/earendil-works/pi
- Tag: `v1.6.0`, commit `faac585884ae2c013a6b1400f3e9e77f10b34bac`
- Licence: MIT
- Packages: `@earendil-works/pi-agent-core`, `@earendil-works/pi-ai` and
  `@earendil-works/pi-coding-agent`, all version `1.6.0`.
- Artifact hashes and the reason the upstream `badlogic/pi-mono` name redirects
  are recorded in `docs/architecture/dependency-pins.md`.

Pi is used in the Milestone 0 spike and the Milestone 1 runtime through its
public TypeScript APIs only. No Pi source is copied into this repository. The
runtime declares `pi-agent-core` and `pi-ai` as exact dependencies; the third
pinned package, `pi-coding-agent`, is not loaded.

## OpenLIT (Milestone 0 pin)

- Project: openlit/openlit — https://github.com/openlit/openlit
- Tag: `openlit-2.2.0`, commit `463a1c1b3cd72a94fab4155efe0f28d90d87fe95`
- Repository licence: Apache License 2.0
- Python SDK: `openlit` `1.45.0`, declared Apache-2.0; wheel
  `sha256:9616c3210410649403280b6fbae770c11add04a776136db7ef2c60634821c25e`.
- TypeScript SDK: `openlit` `1.15.0`, whose `package.json` declares ISC while
  the repository declares Apache-2.0. Both declarations are recorded here; no
  stronger claim is made.

## Milestone 1 runtime and image dependencies

- Python packages pinned in `pyproject.toml`: FastAPI 0.165.0, uvicorn 0.54.0,
  Pydantic 2.14.4, SQLAlchemy 2.1.9, psycopg 3.3.9, redis 8.1.0, httpx 0.28.1,
  PyYAML 6.0.4, Click 8.5.1; test tooling pytest 9.2.0 and Ruff 0.17.6.
  Build backend: hatchling 1.28.0.
- TypeScript tooling pinned in `apps/runtime/package.json`: TypeScript 5.9.3,
  tsx 4.23.15 and `@types/node` 22.19.19.
- Container images pinned in `compose.yaml` and the Dockerfiles:
  `postgres:17.6-alpine`, `redis:8.0.3-alpine`, `python:3.12.12-slim`,
  `node:22.19.0-alpine` and `ghcr.io/astral-sh/uv:0.10.7`.

FastAPI, Starlette, Pydantic, SQLAlchemy, psycopg, Redis, Click, uvicorn and
httpx are MIT/BSD/Apache-2.0 licensed upstream; the authoritative declarations
are in each installed distribution. No licence claim is made for a package
until its pinned version has been resolved in the committed lockfile.

## Pending pinning for later milestones

- React, Vite, Tailwind CSS and other frontend dependencies
- OpenTelemetry SDK packages and OpenLIT instrumentation (Milestone 5)
- LiteLLM is not a kartā dependency. Any LiteLLM use belongs to Marga and is
  recorded in that repository's notices, not here. See ADR-003.
