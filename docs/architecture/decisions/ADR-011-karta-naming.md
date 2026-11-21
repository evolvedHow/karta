# ADR-011: Product name, ASCII identifiers and repository boundary

Status: Accepted at scaffold time.

## Context

The imported architecture specification uses "Agent OS" as a working title. The
predecessor repository, `sutracoder`, is a Go CLI harness with a different
architecture and is not a shipped product. A new repository is needed, and the
naming must be settled before identifiers spread into code, configuration and
deployment manifests.

## Decision

- The product is named **kartā**, Sanskrit कर्ता, "the doer" or "the agent".
- All machine-facing identifiers use ASCII `karta`: repository, binary, Python
  distribution and import module, config and data directories, `KARTA_*`
  environment variables and the worker-env vault context.
- "Agent OS" in the imported specification is read as "kartā".
- A new repository, `~/codebox/karta`, holds the platform.
- `~/codebox/sutracoder` is frozen at tag `sutracoder-v1-final`, remains as a
  reference, is not shipped and receives no further changes.

## Consequences

- The Go code, TUI, provider adapters and local store are not reused. Behaviours
  and test scenarios are carried across through
  `docs/architecture/carry-over-from-sutracoder.md`.
- Existing sutracoder configuration and session data are not migrated; there is
  no compatibility obligation because the tool is not shipped.
- Contributors must not introduce `agentos`, `agent-os` or `sutracoder`
  identifiers into new work.
