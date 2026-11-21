# Pi compatibility spike

Status: **planned — not yet executed.** Milestone 0, §25 of the architecture
specification.

## Objective

Prove that the Pi TypeScript SDK can be embedded behind an internal
`AgentRuntime` adapter and can drive a coding task through Marga with streaming,
tool calling and correlated traces.

The `AgentRuntime` interface in §6.1 is a platform contract, not a claim about
Pi's native method signatures. Do not assume it maps directly.

## Inputs required before starting

- The exact Pi SDK repository commit or package version to pin. The spec names
  `badlogic/pi-mono` but pins no version.
- Confirmation of whether programmatic embedding is supported by that version,
  or whether only the interactive TUI is available.
- The authoritative Marga baseline, per `docs/architecture/current-state-marga.md`.
- A model endpoint reachable from the development host for the end-to-end call.

## Procedure

1. Pin the Pi SDK version in a throwaway spike workspace and record the exact
   resolved version, lockfile hash and licence.
2. Read the installed SDK's exported types and runtime entry points. Document
   the real API surface before writing any adapter.
3. Implement a thin adapter from the installed SDK to the §6.1 contract. Record
   every method that has no native equivalent and the chosen mapping.
4. Configure Pi to send model requests to Marga using whatever custom
   model/provider mechanism that SDK version actually supports.
5. Exercise a minimal coding task with one tool call. Capture the request and
   response at the Marga boundary.
6. Exercise streaming and non-streaming paths separately.
7. Issue an interrupt mid-tool and record how the SDK surfaces cancellation.
8. Persist a session reference, replace the runtime process and resume from it.
9. Propagate one correlation ID through Pi → Marga → provider and verify it is
   visible in the trace backend.

## Compatibility matrix to complete

| Capability | Pi behaviour observed | Adapter mapping | Evidence |
|---|---|---|---|
| Tool calling |  |  |  |
| Streaming deltas |  |  |  |
| Structured output |  |  |  |
| Usage reporting |  |  |  |
| Model metadata |  |  |  |
| Session artifact persistence |  |  |  |
| Interrupt / cancellation |  |  |  |

Leave cells blank until verified. Do not fill them from documentation alone.

## Exit criteria

An end-to-end minimal Pi → Marga → model call works with streaming, tool calling
and trace correlation demonstrated. Protocol gaps and compatibility decisions
are recorded here, and the pinned version is committed.

## Outputs required by §27

- This document, completed with findings.
- `docs/architecture/openlit-instrumentation-spike.md`, completed.
- `docs/architecture/current-state-marga.md`, already inventoried.
- A minimal end-to-end proof of concept.
- A list of decisions or missing source artifacts requiring maintainer input.
