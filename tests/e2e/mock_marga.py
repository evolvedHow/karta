#!/usr/bin/env python3
"""Deterministic OpenAI-compatible Marga stand-in for Milestone 1 E2E checks.

It mirrors the Milestone 0 wire format but asks for ``write_file`` so the
verification script can prove a coding task changed a local test repository.
"""

from __future__ import annotations

import argparse
import json
import uuid
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse


def create_app() -> FastAPI:
    """Build the mock Marga application.

    Returns:
        FastAPI app with ``POST /v1/chat/completions`` and ``GET /health``.

    """
    app = FastAPI(title="karta-e2e-mock-marga", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Report liveness."""
        return {"status": "ok"}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Any:
        """Return a tool call first and a streamed final answer afterwards."""
        body: dict[str, Any] = await request.json()
        completion_id = f"chatcmpl-e2e-{uuid.uuid4().hex}"
        model = str(body.get("model", "strong"))
        tool_result_present = any(
            message.get("role") == "tool" for message in body.get("messages", [])
        )
        return StreamingResponse(
            _stream(completion_id, model, tool_result_present),
            media_type="text/event-stream",
        )

    return app


def _chunk(
    completion_id: str,
    model: str,
    delta: dict[str, Any],
    finish: str | None = None,
    usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build one streaming completion chunk."""
    payload: dict[str, Any] = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": 1,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    if usage is not None:
        payload["usage"] = usage
    return payload


def _encode(payload: dict[str, Any]) -> bytes:
    """Encode a payload as an SSE frame."""
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode("utf-8")


async def _stream(
    completion_id: str, model: str, tool_result_present: bool
) -> AsyncIterator[bytes]:
    """Yield either the tool call or the final answer stream."""
    if tool_result_present:
        for piece in ("Wrote ", "the note."):
            yield _encode(_chunk(completion_id, model, {"content": piece}))
        yield _encode(
            _chunk(
                completion_id,
                model,
                {},
                finish="stop",
                usage={"prompt_tokens": 34, "completion_tokens": 5, "total_tokens": 39},
            )
        )
    else:
        yield _encode(
            _chunk(
                completion_id,
                model,
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call_write_1",
                            "type": "function",
                            "function": {"name": "write_file", "arguments": ""},
                        }
                    ],
                },
            )
        )
        for piece in ('{"path":', '"note.txt",', '"content":', '"hello kartā"}'):
            yield _encode(
                _chunk(
                    completion_id,
                    model,
                    {"tool_calls": [{"index": 0, "function": {"arguments": piece}}]},
                )
            )
        yield _encode(
            _chunk(
                completion_id,
                model,
                {},
                finish="tool_calls",
                usage={"prompt_tokens": 24, "completion_tokens": 12, "total_tokens": 36},
            )
        )
    yield b"data: [DONE]\n\n"


def main() -> None:
    """Start the mock Marga server."""
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8092)
    args = parser.parse_args()
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
