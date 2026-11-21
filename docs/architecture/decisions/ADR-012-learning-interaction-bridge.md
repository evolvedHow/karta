# ADR-012: Preserving the schema-1 interaction contract

Status: Accepted at scaffold time.

## Context

`sutracoder` emits one JSON object per tool interaction to a per-session JSONL
file. That record is the primary ingestion surface of a separate self-improving
execution engine specified in `requirements/recursive-learn.md`. The kartā
architecture does not describe this contract, and its platform design has no
place for a local per-session file emitter: runtime processes are replaceable,
tasks are multi-tenant and PostgreSQL is authoritative.

Silently dropping the contract would break a working cross-project integration.
Reimplementing the emitter inside the platform would add a second, inconsistent
source of interaction truth.

## Decision

- The schema-1 record shape remains a stable external contract.
- kartā emits structured, tenant-scoped task and tool events with sequence
  numbers and correlation IDs, as specified in §6.4.
- A downstream event consumer derives the legacy JSONL records from those
  events. The consumer lives outside the platform's runtime and control plane.
- No JSONL emitter is added to `apps/runtime`, `apps/api` or `apps/worker`.

## Consequences

- The platform's event schema must carry every field the legacy record needs:
  session and turn identity, goal, tool name and arguments, status, stdout,
  stderr, return code, duration, truncation flag, tool error, correction signal,
  token counts and session status.
- The consumer becomes a compatibility boundary; changes to the record shape
  bump `schema` in the consumer, not in the platform.
- The self-improvement engine's vector memory, distillation and retrieval remain
  out of scope for kartā.
- Porting the consumer is work for a later milestone and is not part of
  Milestone 0.
