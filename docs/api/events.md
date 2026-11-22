# Structured event schema (Milestone 1)

`AgentEvent` is the single event contract persisted in `task_events`, returned
by the API and emitted by the TypeScript runtime. It replaces a direct JSONL
writer: the downstream consumer derives the schema-1 record from these events
(ADR-012).

```json
{
  "event_id": "7d2f...",
  "tenant_id": "tenant-a",
  "task_id": "b90c...",
  "session_id": "b90c...",
  "sequence": 3,
  "event_type": "tool.completed",
  "occurred_at": "2026-11-22T02:05:35.578Z",
  "payload": { "tool_name": "write_file", "is_error": false },
  "correlation_id": "6a1e...",
  "trace_id": null
}
```

| Field | Type | Notes |
|---|---|---|
| `event_id` | string (UUID) | Unique event identifier. |
| `tenant_id` | string | Owner tenant; never taken from a client body. |
| `task_id` | string | Durable task identifier. |
| `session_id` | string | Pi session identifier; equals `task_id` in Milestone 1. |
| `sequence` | integer ≥ 1 | Monotonic per task; `UNIQUE(task_id, sequence)`. |
| `event_type` | enum | Values below. |
| `occurred_at` | ISO-8601 UTC | Ends in `Z`. |
| `payload` | object | Event-specific, never internal reasoning. |
| `correlation_id` | string or null | Propagated from the originating API request. |
| `trace_id` | string or null | Reserved for OpenLIT instrumentation in Milestone 5. |

## Event types

| Type | Emitter | Payload keys |
|---|---|---|
| `task.created` | Control plane | `profile_id`, `profile_version` |
| `task.started` | Control plane | `correlation_id` |
| `message.delta` | Pi runtime | `delta` |
| `message.complete` | Pi runtime | `{}` |
| `tool.started` | Pi runtime | `tool_name` |
| `tool.completed` | Pi runtime | `tool_name`, `is_error` |
| `usage.recorded` | Control plane | `input_tokens`, `output_tokens`, `total_tokens` |
| `task.completed` | Control plane | `stop_reason` |
| `task.failed` | Control plane | `error` |

Private chain-of-thought is never emitted. Tool payloads contain names and
status, not credentials or full provider prompts.

## Ordering and replay

The control plane emits `task.created` (sequence 1) and `task.started`
(sequence 2). Runtime events are renumbered by the worker to continue the
existing sequence. `usage.recorded` and the terminal event follow. SSE uses
the sequence as its `id`, so `Last-Event-ID` resumes exactly after the last
delivered event.
