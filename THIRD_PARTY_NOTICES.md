# Third-party notices

This file records attribution obligations for components kartā depends on or
evolves. It is not a complete software bill of materials; a pinned SBOM is
produced as the platform packages are built in Milestone 1 and later.

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

Pi is used in the spike through its public TypeScript APIs only. No Pi source
is copied into this repository.

## OpenLIT (Milestone 0 pin)

- Project: openlit/openlit — https://github.com/openlit/openlit
- Tag: `openlit-2.2.0`, commit `463a1c1b3cd72a94fab4155efe0f28d90d87fe95`
- Repository licence: Apache License 2.0
- Python SDK: `openlit` `1.45.0`, declared Apache-2.0; wheel
  `sha256:9616c3210410649403280b6fbae770c11add04a776136db7ef2c60634821c25e`.
- TypeScript SDK: `openlit` `1.15.0`, whose `package.json` declares ISC while
  the repository declares Apache-2.0. Both declarations are recorded here; no
  stronger claim is made.

OpenTelemetry SDK packages, FastAPI, Pydantic, uvicorn and httpx are installed
as transitive or explicit pinned dependencies of the spike. Their exact
resolved versions are in the committed `uv.lock` and `package-lock.json`.

## Pending pinning for later milestones

- PostgreSQL, Redis and container base images
- React, Vite, Tailwind CSS and other frontend dependencies
- LiteLLM is not a kartā dependency. Any LiteLLM use belongs to Marga and is
  recorded in that repository's notices, not here. See ADR-003.

No licence claim is made for these components until their pinned versions have
been inspected.
