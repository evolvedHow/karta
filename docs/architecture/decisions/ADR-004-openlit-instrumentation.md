# ADR-004: OpenLIT and OpenTelemetry instrumentation

Status: Accepted after the Milestone 0 compatibility spike.

## Context

Observability must correlate a task across the TypeScript runtime, Marga and
the model backend without sending credentials to the model or logging them.
OpenLIT exists in both Python and TypeScript flavours; their OTLP exporters
behave differently.

## Decision

- OpenLIT is initialized in both processes with loopback OTLP export and
  explicit application names.
- W3C `traceparent` is injected by the TS runtime into model requests. Marga's
  own transport does not forward arbitrary headers, so OpenLIT HTTP
  instrumentation is required on the gateway side.
- The spike receiver accepts protobuf from Python OpenLIT and OTLP JSON from
  TypeScript OpenLIT. OTLP JSON ids are decoded as hex, not with protobuf's
  generic base64 JSON mapping.
- Short-lived CLI processes flush and shut down the tracer provider before
  exit.
- No schema-1 JSONL emitter is added; structured events are consumed downstream
  per ADR-012.

## Consequences

- Correlation is verified by an automated check that requires one trace id in
  the runtime span, gateway spans and headers seen by the backend.
- Credentials are never attached to spans or injected headers.
- A full OpenLIT backend is not required for development; the loopback receiver
  is sufficient for verification.
