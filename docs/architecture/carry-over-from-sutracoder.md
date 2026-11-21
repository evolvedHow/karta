# Carry-over from sutracoder

`sutracoder` is frozen at `sutracoder-v1-final` and is not shipped. **No Go code
is ported into kartā.** This document records behaviours, safety rules and test
scenarios worth re-expressing in the new architecture. It is a specification of
intent, not an inventory of reusable source.

The frozen repository is at `~/codebox/sutracoder`. Its spec of record is
`requirements/initial_prompt.md`.

## Behaviours worth preserving

| Behaviour | Frozen implementation | Destination in kartā |
|---|---|---|
| Structured tool result shape | `tools.Result`: status, stdout, stderr, returncode, duration, truncated | Pi runtime event payloads; shared event schema in `packages/shared-types` |
| Observation rendering | Head+tail truncation with an explicit marker so the model knows more exists | Context Engine tool-output management (§8.4) |
| Error taxonomy | Recoverable `ToolError` fed back to the model; loop-stopping `FatalError` surfaced to the user | Runtime event types `tool.failed` vs `task.failed`; control plane failure classification |
| Hard bounds | Max turns, cumulative token budget, clean halt with status | Task budget enforcement (§20.2) — now cost, tokens, iterations, tool calls, time and child budget |
| Cancellation | Root `context.Context`, in-flight tool cancelled, partial output retained and marked interrupted | `task.cancelled`, interrupt propagation through runtime and tool broker |
| Retry policy | Bounded exponential backoff on 429/5xx; auth and protocol errors fatal | Marga routing/fallback and provider error normalisation (§5.6, §5.7) |
| Compaction policy | Summarise older turns, keep system prompt and recent turns raw, never lose source rows | Context Engine compaction (§8.5) — keep original events for audit and replay |
| Path confinement | Every tool path resolved under one workspace root; `..` and absolute escapes rejected | Execution-plane workspace isolation (§13); container boundary replaces the Go check but the invariant remains |
| Shell denylist | Regex denylist for sudo, recursive rm, mkfs, force push, dd to devices, fork bombs | Permission engine risk levels A0–A3 and approval binding (§11), not a string match in the agent process |
| Approval gate | Restricted tool prompts for a yes/no decision before execution | Durable approval service with payload-hash binding and released workers (§11.2) |
| Vault resolution | Environment first, provider vault context, then shared default; short timeout; never log keys | `SecretManager` interface (§13.4), context `karta`, same precedence |
| Credential redaction | Keys and full prompts never written to logs | Sensitive-data policy (§9.3), metadata-only telemetry by default in shared mode |
| Event-driven view | Loop emits events; TUI holds no agent state | Event schema and SSE (§6.4, §15.4) with tenant/task/session IDs and sequence numbers |

## Test scenarios to port

These golden scenarios from `internal/agent/loop_test.go` are worth rewriting as
runtime/API integration tests:

1. Plan → write file → complete goal, with the resulting artifact verified on
   disk and the plan state asserted.
2. Tool failure → observation fed back → corrected retry → success, asserting
   the correction signal.
3. Cancellation mid-tool: partial output preserved, status `cancelled`, session
   resumable.
4. Token and turn limits: clean halt, correct terminal state, no further model
   calls.
5. Provider auth failure classified fatal; transient 429 retried with bounded
   backoff.
6. Path escape attempts rejected from file and shell tools.
7. Denylisted shell commands require confirmation even in autonomous mode.

Each ported test belongs in `tests/integration/` or `tests/tenant-isolation/`,
never in the frozen repository.

## Explicitly not carried over

- The Go `AgentLoop`. Pi owns execution; kartā must not build a new general
  purpose loop (§1.1).
- The five Go provider adapters. Marga owns provider abstraction and routing.
- The SQLite schema, single-connection store and JSONL emitter. PostgreSQL is
  authoritative; the schema-1 contract survives via ADR-012.
- The Bubble Tea TUI and its slash-command controller. The CLI becomes an API
  client; the web UI is React.
- TOML config resolution and `SUTRACODER_*` environment handling.
- In-process approval channels. Approval state must be durable.

## Interaction emission

The schema-1 JSONL record is a cross-project contract with the separate
self-improvement engine described in `requirements/recursive-learn.md`. It is
preserved by a downstream event consumer, as decided in ADR-012. The platform
emits structured events; it does not write JSONL sidecars.
