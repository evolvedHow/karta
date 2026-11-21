# ADR-001: Pi SDK integration boundary

Status: Accepted after the Milestone 0 compatibility spike.

## Context

Pi owns the agent loop, tool execution and provider request encoding. The
platform needs a stable boundary that does not depend on private Pi internals,
and the pinned upstream API must be inspected before an adapter is written.

## Decision

- The TypeScript runtime owns the Pi adapter. Python does not import or wrap Pi
  code.
- The adapter uses the public `Agent` API from `@earendil-works/pi-agent-core`
  and the `openai-completions` model plus `streamSimple` from
  `@earendil-works/pi-ai/compat`.
- Marga is reached through the model's `baseUrl` and request `headers`; no Pi
  source is modified and no provider credentials are placed in model objects.
- Pi lifecycle events are normalized into tenant-scoped platform events with
  sequence numbers and correlation IDs. No JSONL emitter is added.
- Versions are pinned by `spikes/milestone-0/pi-runtime/package.json` and its
  lockfile, recorded in `docs/architecture/dependency-pins.md`.

## Consequences

- Tool schemas and event names are validated by typechecked adapter tests in
  every milestone that changes the boundary.
- A Pi upgrade requires re-inspection of the pinned type declarations before
  the adapter is changed.
- The spike proved streaming, tool calling and trace propagation through this
  boundary; see `docs/architecture/milestone-0-spike-results.md`.
