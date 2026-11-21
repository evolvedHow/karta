#!/usr/bin/env python3
"""Run the existing Marga tree read-only with OpenLIT instrumentation.

The local ``~/codebox/marga`` checkout is deliberately not modified. This
launcher imports it from an explicit path, builds a small loopback-only proxy
with a real llama.cpp backend and the deterministic tool-call mock provider,
and exports OpenTelemetry spans to the spike's OTLP receiver.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Awaitable, Callable, Mapping

import openlit
import uvicorn

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8011
DEFAULT_MARGA_PATH = "/home/vgana/codebox/marga"
LLAMA_MODEL = "Hermes-3-Llama-3.1-8B.Q4_K_M"


def _record_incoming_headers(scope: Mapping[str, Any], output_path: str) -> None:
    """Append selected incoming headers for trace-correlation evidence.

    Args:
        scope: ASGI connection scope.
        output_path: JSON-lines artifact path.

    """
    headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in scope.get("headers", [])
    }
    captured = {
        key: headers[key]
        for key in ("traceparent", "tracestate", "x-karta-task-id")
        if key in headers
    }
    if not captured:
        return
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(captured, sort_keys=True) + "\n")


def _header_capture_middleware(
    app: Callable[..., Awaitable[None]], output_path: str
) -> Callable[..., Awaitable[None]]:
    """Wrap an ASGI app with incoming trace-header capture.

    Args:
        app: ASGI application callable.
        output_path: JSON-lines artifact path.

    Returns:
        ASGI application callable with header capture installed.

    """

    async def wrapped(
        scope: dict[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Any],
    ) -> None:
        """Capture headers on HTTP requests then delegate to the wrapped app."""
        if scope["type"] == "http":
            _record_incoming_headers(scope, output_path)
        await app(scope, receive, send)

    return wrapped


def create_app(marga_path: str, captured_headers: str) -> Any:
    """Build the instrumented Marga application.

    Args:
        marga_path: Filesystem path to the read-only Marga checkout.
        captured_headers: JSON-lines path for incoming trace headers.

    Returns:
        FastAPI application served by the spike launcher.

    Raises:
        ImportError: When Marga cannot be imported from ``marga_path``.

    """
    if marga_path not in sys.path:
        sys.path.insert(0, marga_path)
    try:
        from marga import Proxy
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ImportError(f"Cannot import Marga from {marga_path}") from exc

    backends: dict[str, dict[str, Any]] = {
        "llama": {
            "base_url": os.environ.get("KARTA_SPIKE_LLAMA_URL", "http://127.0.0.1:8080/v1"),
            "models": [LLAMA_MODEL],
        },
        "mock-hosted": {
            "base_url": os.environ.get("KARTA_SPIKE_MOCK_URL", "http://127.0.0.1:8091/v1"),
            "models": ["mock-tool"],
        },
    }
    proxy = Proxy(backends=backends, name="karta-marga-spike", vault_context="karta")
    # Pin the spike to the deterministic tool-call backend. The local llama.cpp
    # model does not reliably emit tool calls, and LeastUsed would otherwise
    # select it for the default route.
    proxy.route(lambda _ctx: "mock-hosted/mock-tool")
    app = proxy.build_app()
    return _header_capture_middleware(app, captured_headers)


def parse_args() -> argparse.Namespace:
    """Parse launcher command-line options.

    Returns:
        Parsed arguments containing host, port, Marga path and capture path.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--marga-path", default=DEFAULT_MARGA_PATH)
    parser.add_argument("--captured-headers", default="artifacts/marga-headers.jsonl")
    return parser.parse_args()


def main() -> None:
    """Initialize OpenLIT and serve the instrumented Marga application."""
    args = parse_args()
    openlit.init(
        application_name="karta-marga-spike",
        environment="spike",
        otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318"),
        disable_batch=True,
        disable_metrics=True,
        disable_events=True,
    )
    uvicorn.run(
        create_app(args.marga_path, args.captured_headers),
        host=args.host,
        port=args.port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
