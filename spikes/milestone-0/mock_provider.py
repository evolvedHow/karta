#!/usr/bin/env python3
"""Deterministic OpenAI-compatible provider used by the Milestone 0 spike.

The local llama.cpp model available on this machine does not reliably emit
tool calls. This stub stands in for a hosted provider and returns one ``add``
tool call followed by a final answer, using the same OpenAI wire format that
Marga forwards. It also records the incoming W3C ``traceparent`` header so the
verification script can prove propagation through Marga.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8091
TOOL_NAME = "add"


def _record_headers(headers: Any, output_path: str) -> None:
    """Append selected trace headers received by the mock provider.

    Args:
        headers: Incoming ASGI headers mapping.
        output_path: JSON-lines artifact path.

    """
    captured = {
        key.lower(): headers.get(key)
        for key in ("traceparent", "tracestate", "x-karta-task-id")
        if headers.get(key)
    }
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(captured, sort_keys=True) + "\n")


def _tool_call_payload(model: str, completion_id: str) -> dict[str, Any]:
    """Build a non-streaming completion carrying the ``add`` tool call.

    Args:
        model: Model identifier echoed back to the caller.
        completion_id: Unique completion identifier.

    Returns:
        OpenAI-shaped completion payload.

    """
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_add_1",
                            "type": "function",
                            "function": {
                                "name": TOOL_NAME,
                                "arguments": json.dumps({"a": 2, "b": 2}, separators=(",", ":")),
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 24, "completion_tokens": 12, "total_tokens": 36},
    }


def _final_payload(model: str, completion_id: str) -> dict[str, Any]:
    """Build the non-streaming final answer after the tool result.

    Args:
        model: Model identifier echoed back to the caller.
        completion_id: Unique completion identifier.

    Returns:
        OpenAI-shaped completion payload.

    """
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "The sum is 4."},
            }
        ],
        "usage": {"prompt_tokens": 34, "completion_tokens": 5, "total_tokens": 39},
    }


def _chunk(
    completion_id: str,
    model: str,
    delta: dict[str, Any],
    finish: str | None = None,
    usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build one OpenAI chat-completion streaming chunk.

    Args:
        completion_id: Identifier shared by all chunks in one completion.
        model: Model identifier echoed back to the caller.
        delta: Incremental message content.
        finish: Finish reason on the terminal chunk.
        usage: Token usage on the terminal chunk.

    Returns:
        OpenAI-shaped streaming chunk.

    """
    payload: dict[str, Any] = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    if usage is not None:
        payload["usage"] = usage
    return payload


def _encode_chunk(payload: dict[str, Any]) -> bytes:
    """Encode one payload as an SSE ``data:`` frame.

    Args:
        payload: Chunk payload to encode.

    Returns:
        UTF-8 encoded SSE frame.

    """
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode("utf-8")


async def _tool_stream(completion_id: str, model: str) -> AsyncIterator[bytes]:
    """Yield the tool-call completion as SSE frames.

    Args:
        completion_id: Identifier shared by all chunks in one completion.
        model: Model identifier echoed back to the caller.

    Yields:
        Encoded SSE frames followed by the ``[DONE]`` sentinel.

    """
    yield _encode_chunk(
        _chunk(
            completion_id,
            model,
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_add_1",
                        "type": "function",
                        "function": {"name": TOOL_NAME, "arguments": ""},
                    }
                ],
            },
        )
    )
    for piece in ('{"a":', "2,", '"b":', "2}"):
        yield _encode_chunk(
            _chunk(
                completion_id,
                model,
                {"tool_calls": [{"index": 0, "function": {"arguments": piece}}]},
            )
        )
    yield _encode_chunk(
        _chunk(
            completion_id,
            model,
            {},
            finish="tool_calls",
            usage={"prompt_tokens": 24, "completion_tokens": 12, "total_tokens": 36},
        )
    )
    yield b"data: [DONE]\n\n"


async def _final_stream(completion_id: str, model: str) -> AsyncIterator[bytes]:
    """Yield the final answer as SSE frames.

    Args:
        completion_id: Identifier shared by all chunks in one completion.
        model: Model identifier echoed back to the caller.

    Yields:
        Encoded SSE frames followed by the ``[DONE]`` sentinel.

    """
    for piece in ("The ", "sum ", "is ", "4."):
        yield _encode_chunk(_chunk(completion_id, model, {"content": piece}))
    yield _encode_chunk(
        _chunk(
            completion_id,
            model,
            {},
            finish="stop",
            usage={"prompt_tokens": 34, "completion_tokens": 5, "total_tokens": 39},
        )
    )
    yield b"data: [DONE]\n\n"


def create_app(output_path: str) -> FastAPI:
    """Build the mock provider application.

    Args:
        output_path: JSON-lines path for captured trace headers.

    Returns:
        FastAPI application exposing ``POST /v1/chat/completions`` and
        ``GET /health``.

    """
    app = FastAPI(title="karta-mock-provider", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Report provider readiness."""
        return {"status": "ok"}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Any:
        """Return either the tool call or the final answer, streaming if asked."""
        _record_headers(request.headers, output_path)
        body: dict[str, Any] = await request.json()
        completion_id = f"chatcmpl-mock-{uuid.uuid4().hex}"
        model = str(body.get("model", "mock-tool"))
        tool_result_present = any(
            message.get("role") == "tool" for message in body.get("messages", [])
        )
        if tool_result_present:
            payload = _final_payload(model, completion_id)
            stream = _final_stream(completion_id, model)
        else:
            payload = _tool_call_payload(model, completion_id)
            stream = _tool_stream(completion_id, model)
        if body.get("stream"):
            return StreamingResponse(stream, media_type="text/event-stream")
        return payload

    return app


def parse_args() -> argparse.Namespace:
    """Parse mock provider command-line options.

    Returns:
        Parsed arguments containing host, port and capture path.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--captured-headers", default="artifacts/mock-headers.jsonl")
    return parser.parse_args()


def main() -> None:
    """Start the loopback mock provider until interrupted."""
    import uvicorn

    args = parse_args()
    uvicorn.run(
        create_app(args.captured_headers), host=args.host, port=args.port, log_level="warning"
    )


if __name__ == "__main__":
    main()
