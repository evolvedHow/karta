"""Unit tests for the Milestone 0 compatibility spike helpers."""

from __future__ import annotations

import asyncio
import io
import json
from typing import Any

import httpx

from mock_provider import create_app
from otlp_receiver import decode_export_request, read_body
from verify_spike import verify


class _FakeHandler:
    """Minimal stand-in for a request handler used by ``read_body``."""

    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        """Store the encoded body and headers.

        Args:
            body: Encoded request body.
            headers: Case-insensitive header mapping.

        """
        self.rfile = io.BytesIO(body)
        self.headers = headers


def _json_frame(trace_id: str, span_id: str) -> bytes:
    """Build an OTLP/JSON export frame with one span.

    Args:
        trace_id: Lowercase hex trace id.
        span_id: Lowercase hex span id.

    Returns:
        UTF-8 encoded OTLP JSON payload.

    """
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "svc"}}]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "openlit"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": span_id,
                                "kind": 3,
                                "name": "karta.spike.task",
                                "attributes": {},
                            }
                        ],
                    }
                ],
            }
        ]
    }
    return json.dumps(payload).encode("utf-8")


def test_json_export_keeps_hex_ids() -> None:
    """OTLP JSON ids must stay hex, not be reinterpreted as base64."""
    trace_id = "0123456789abcdef0123456789abcdef"
    span_id = "0123456789abcdef"
    records = decode_export_request(_json_frame(trace_id, span_id), "application/json")
    assert len(records) == 1
    assert records[0]["trace_id"] == trace_id
    assert records[0]["span_id"] == span_id
    assert records[0]["service_name"] == "svc"
    assert records[0]["kind"] == "SPAN_KIND_CLIENT"


def test_read_body_handles_chunked_encoding() -> None:
    """Read a chunked OTLP request body without losing bytes."""
    body = _json_frame("a" * 32, "b" * 16)
    midpoint = len(body) // 2
    wire = (
        f"{midpoint:x}\r\n".encode()
        + body[:midpoint]
        + b"\r\n"
        + f"{len(body) - midpoint:x}\r\n".encode()
        + body[midpoint:]
        + b"\r\n0\r\n\r\n"
    )
    handler = _FakeHandler(wire, {"Transfer-Encoding": "chunked"})
    assert read_body(handler) == body  # type: ignore[arg-type]


def test_mock_provider_emits_tool_call_then_final_answer(tmp_path: Any) -> None:
    """The deterministic provider completes a two-turn tool loop."""
    asyncio.run(_exercise_mock_provider(tmp_path))


async def _exercise_mock_provider(tmp_path: Any) -> None:
    """Drive the mock provider through one tool loop.

    Args:
        tmp_path: Temporary directory supplied by pytest.

    """
    captured = tmp_path / "headers.jsonl"
    transport = httpx.ASGITransport(app=create_app(str(captured)))
    async with httpx.AsyncClient(transport=transport, base_url="http://mock") as client:
        first = await client.post(
            "/v1/chat/completions",
            json={
                "model": "mock-tool",
                "messages": [{"role": "user", "content": "Add 2 and 2"}],
                "stream": False,
            },
            headers={"traceparent": "00-" + "1" * 32 + "-" + "2" * 16 + "-01"},
        )
        first_payload = first.json()
        tool_calls = first_payload["choices"][0]["message"]["tool_calls"]
        assert tool_calls[0]["function"]["name"] == "add"
        assert json.loads(tool_calls[0]["function"]["arguments"]) == {"a": 2, "b": 2}

        second = await client.post(
            "/v1/chat/completions",
            json={
                "model": "mock-tool",
                "messages": [
                    {"role": "user", "content": "Add 2 and 2"},
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls,
                    },
                    {"role": "tool", "content": "4", "tool_call_id": "call_add_1"},
                ],
            },
        )
        assert second.json()["choices"][0]["message"]["content"] == "The sum is 4."
    assert "traceparent" in json.loads(captured.read_text(encoding="utf-8").splitlines()[0])


def test_verify_spike_accepts_correlated_artifacts(tmp_path: Any) -> None:
    """Verification passes only when runtime, gateway and backend share a trace."""
    trace_id = "c" * 32
    runtime = {
        "trace_id": trace_id,
        "span_id": "a" * 16,
        "service_name": "karta-runtime-spike",
        "name": "karta.spike.task",
        "kind": "SPAN_KIND_CLIENT",
        "attributes": {},
        "scope": "openlit",
    }
    gateway = {**runtime, "service_name": "karta-marga-spike", "span_id": "b" * 16}
    (tmp_path / "spans.jsonl").write_text(
        "\n".join(json.dumps(record) for record in (runtime, gateway)) + "\n",
        encoding="utf-8",
    )
    traceparent = f"00-{trace_id}-{'a' * 16}-01"
    for name in ("marga-headers.jsonl", "mock-headers.jsonl"):
        (tmp_path / name).write_text(
            json.dumps({"traceparent": traceparent}) + "\n",
            encoding="utf-8",
        )
    (tmp_path / "pi-result.json").write_text(
        json.dumps(
            {
                "text": "The sum is 4.",
                "executedTools": ["add"],
                "streamingDeltaCount": 4,
                "events": [
                    {"eventType": "tool_execution_end"},
                    {"eventType": "message_update"},
                ],
            }
        ),
        encoding="utf-8",
    )
    report = verify(tmp_path)
    assert report["status"] == "pass"
    assert report["trace_id"] == trace_id
