# Third-party notices

This file records attribution obligations for components kartā depends on or
evolves. It is not a complete software bill of materials; that is produced once
dependency versions are pinned in Milestone 0 and 1.

## Marga

- Project: marga — https://github.com/evolvedHow/marga
- Local checkout: `~/codebox/marga`, package version `0.2.0`
- Licence: Apache License 2.0
- Notice: "marga — Copyright 2026 Vish Ganapathy. This product includes software
  developed by Vish Ganapathy."

Marga is a separately versioned upstream. kartā does not copy it into this
repository. If gateway code is modified as part of kartā, the modified files
must be identified here and the upstream licence and notice preserved.

## Pending pinning

The following are named in the architecture specification but have no pinned
version in this scaffold. Their licences, notices and SBOM entries must be
recorded here when versions are selected:

- Pi SDK (`badlogic/pi-mono`)
- OpenLIT
- OpenTelemetry instrumentation
- FastAPI, Pydantic, uvicorn, httpx and other Python dependencies
- React, Vite, Tailwind CSS and other frontend dependencies
- PostgreSQL, Redis and container base images

No licence claim is made for these components until the pinned versions have
been inspected.
