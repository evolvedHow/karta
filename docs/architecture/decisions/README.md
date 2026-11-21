# Architecture decision records

Records in this directory follow the plan set out in §28 of the architecture
specification. An ADR is written when the decision is taken, not before.

## Authored from the specification

| ADR | Subject | Status |
|---|---|---|
| [ADR-001](ADR-001-pi-sdk-integration-boundary.md) | Pi SDK integration boundary | Accepted |
| [ADR-002](ADR-002-marga-gateway-boundary.md) | Marga as context/policy/model gateway | Accepted |
| [ADR-003](ADR-003-litellm-adapter-scope.md) | Optional LiteLLM adapter and routing ownership | Accepted, implementation deferred |
| [ADR-004](ADR-004-openlit-instrumentation.md) | OpenLIT and OpenTelemetry instrumentation | Accepted |

## Planned by the specification — not yet authored

| ADR | Subject | Expected milestone |
|---|---|---|
| ADR-005 | Python control plane / TypeScript runtime split | 1 |
| ADR-006 | Docker sandbox isolation model | 4 |
| ADR-007 | PostgreSQL tenant isolation and RLS | 7 |
| ADR-008 | Task/event durability and recovery | 3 |
| ADR-009 | Bangtag syntax and context profile resolution | 2 |
| ADR-010 | Local, dedicated and shared deployment profiles | 8 |

## Adopted at scaffold time

| ADR | Subject | Status |
|---|---|---|
| [ADR-011](ADR-011-karta-naming.md) | Product name, ASCII identifiers and repository boundary | Accepted |
| [ADR-012](ADR-012-learning-interaction-bridge.md) | Preserving the schema-1 interaction contract | Accepted |
