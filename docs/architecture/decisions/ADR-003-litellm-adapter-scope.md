# ADR-003: Optional LiteLLM adapter and routing ownership

Status: Accepted by maintainer decision; implementation deferred.

## Context

Section 1.2 of the architecture specification names LiteLLM as optional. Two
components making independent model decisions would produce conflicting
routing, cost and policy outcomes.

## Decision

- LiteLLM is in scope and may be used behind a Marga adapter.
- Marga remains the only policy and routing authority. LiteLLM is a provider
  integration beneath it, not a second router.
- No LiteLLM version is pinned in Milestone 0 and no LiteLLM code is included in
  the spike. A version is pinned when the adapter is implemented.

## Consequences

- Provider coverage can be extended without changing the Pi boundary.
- Tests must assert that Marga's decision is authoritative whenever LiteLLM is
  configured.
- `THIRD_PARTY_NOTICES.md` gains the LiteLLM licence entry at pin time.
