# OpenLIT instrumentation spike

Status: **planned — not yet executed.** Milestone 0, §25 of the architecture
specification.

## Objective

Prove that OpenLIT can ingest correlated traces from the Pi runtime and the
Marga gateway, using OpenTelemetry-compatible instrumentation, without becoming
the application database or the financial usage ledger.

## Inputs required before starting

- The exact OpenLIT version and installation method to use. The spec names the
  project but pins no version and does not choose a deployment method.
- The OpenTelemetry collector endpoint and protocol available in the local
  Compose environment.
- Confirmation that the local model endpoint can be called during the spike.

## Procedure

1. Pin the OpenLIT version from its documented installation method. Do not
   invent SDK calls; read the installed package or deployment documentation.
2. Stand up the minimum collector/UI needed to receive traces.
3. Instrument the spike's Pi adapter so one session produces a span containing
   the session ID and task ID.
4. Instrument the Marga request path so the same correlation ID appears on the
   gateway span and the provider call.
5. Verify the trace is queryable in OpenLIT with both spans correlated.
6. Confirm that prompt and response content capture is disabled by default and
   that no secret values appear in spans or logs.
7. Confirm that the platform's own usage ledger remains separate from
   observability data, per §9.4.

## Evidence to record

| Check | Result | Evidence |
|---|---|---|
| Pi session span present |  |  |
| Marga request span present |  |  |
| One correlation ID across both |  |  |
| Tool execution span present |  |  |
| Content capture off by default |  |  |
| No secrets in telemetry |  |  |
| Ledger independent of OpenLIT |  |  |

Leave cells blank until verified.

## Exit criteria

OpenLIT shows correlated agent, model and tool traces for the spike task, with
metadata-only capture by default and no secrets in telemetry. Any deviation from
the documented setup is recorded as a decision in
`docs/architecture/decisions/`.
