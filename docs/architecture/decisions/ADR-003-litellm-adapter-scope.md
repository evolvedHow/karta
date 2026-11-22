# ADR-003: LiteLLM belongs to Marga, not kartā

Status: Accepted by maintainer decision; kartā has no LiteLLM work item.

## Context

Section 1.2 of the architecture specification names LiteLLM as optional. The
maintainer confirmed that LiteLLM is a Marga concern: Marga owns provider
adapters and routing policy, while kartā consumes Marga's documented
OpenAI-compatible surface. Two components making independent model decisions
would produce conflicting routing, cost and policy outcomes.

## Decision

- kartā does not implement, configure, pin or test a LiteLLM adapter.
- Any LiteLLM use stays inside Marga, which remains the sole policy and routing
  authority. kartā integrates only with Marga.
- The Pi runtime reaches providers through Marga's OpenAI-compatible HTTP
  surface. Provider changes are made in Marga, not in kartā.
- No LiteLLM dependency is added to any kartā package or container image.

## Consequences

- Provider coverage can change in Marga without a kartā release.
- Tests at the kartā boundary assert that requests and trace headers reach
  Marga; they do not assert which upstream provider Marga selected.
- Marga upstream remains responsible for LiteLLM licensing and notices. This
  repository makes no LiteLLM licence claim and lists no LiteLLM pin.
