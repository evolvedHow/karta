#!/usr/bin/env python3
"""Minimal loopback OTLP/HTTP trace receiver for the Milestone 0 spike.

The receiver stores decoded spans as JSON lines so the verification script can
assert trace correlation without running a full OpenLIT backend. It listens on
127.0.0.1 only. Both protobuf and JSON OTLP/HTTP encodings are accepted because
the Python OpenLIT exporter uses protobuf while the TypeScript exporter uses
JSON with chunked transfer encoding.
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from opentelemetry.proto.collector.trace.v1 import trace_service_pb2
from opentelemetry.proto.trace.v1 import trace_pb2

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4318


def _attribute_value(value: Any) -> Any:
    """Return the scalar carried by an OTel ``AnyValue`` message.

    Args:
        value: An ``opentelemetry.proto.common.v1.AnyValue`` message.

    Returns:
        The decoded scalar, list or mapping value.

    """
    kind = value.WhichOneof("value")
    if kind is None:
        return None
    if kind == "array_value":
        return [_attribute_value(item) for item in value.array_value.values]
    if kind == "kvlist_value":
        return {item.key: _attribute_value(item.value) for item in value.kvlist_value.values}
    return getattr(value, kind)


def _attributes(message: Any) -> dict[str, Any]:
    """Decode an OTel repeated ``KeyValue`` field into a plain dictionary.

    Args:
        message: A protobuf message exposing an ``attributes`` field.

    Returns:
        Mapping of attribute names to decoded values.

    """
    return {item.key: _attribute_value(item.value) for item in message.attributes}


def _json_attribute_value(value: dict[str, Any]) -> Any:
    """Decode one OTLP JSON ``AnyValue`` object.

    Args:
        value: OTLP JSON value object.

    Returns:
        Decoded scalar, list or mapping value.

    """
    for key in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if key in value:
            return value[key]
    if "arrayValue" in value:
        return [_json_attribute_value(item) for item in value["arrayValue"].get("values", [])]
    if "kvlistValue" in value:
        return _json_attributes(value["kvlistValue"].get("values", []))
    return None


def _json_attributes(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Decode an OTLP JSON attribute list.

    Args:
        items: List of OTLP JSON ``KeyValue`` objects.

    Returns:
        Mapping of attribute names to decoded values.

    """
    return {item["key"]: _json_attribute_value(item.get("value", {})) for item in items}


def _kind_name(kind: int) -> str:
    """Return the protobuf name of an OTel span kind.

    Args:
        kind: Numeric span kind.

    Returns:
        Span kind name, or ``SPAN_KIND_UNSPECIFIED`` for unknown values.

    """
    try:
        return trace_pb2.Span.SpanKind.Name(kind)
    except ValueError:
        return "SPAN_KIND_UNSPECIFIED"


def decode_json_export_request(payload: bytes) -> list[dict[str, Any]]:
    """Decode an OTLP/HTTP JSON trace export request.

    The OTLP JSON specification encodes ids as lowercase hex. Passing those
    strings to protobuf's generic JSON parser would interpret them as base64,
    so the JSON tree is decoded directly instead.

    Args:
        payload: UTF-8 encoded OTLP JSON body.

    Returns:
        One dictionary per span with hex ids, name, kind, service name,
        attributes and parent span id.

    """
    data = json.loads(payload.decode("utf-8"))
    records: list[dict[str, Any]] = []
    for resource_spans in data.get("resourceSpans", []):
        resource_attrs = _json_attributes(resource_spans.get("resource", {}).get("attributes", []))
        service_name = resource_attrs.get("service.name", "unknown")
        for scope_spans in resource_spans.get("scopeSpans", []):
            scope_name = scope_spans.get("scope", {}).get("name", "")
            for span in scope_spans.get("spans", []):
                records.append(
                    {
                        "trace_id": span.get("traceId", ""),
                        "span_id": span.get("spanId", ""),
                        "parent_span_id": span.get("parentSpanId") or None,
                        "name": span.get("name", ""),
                        "kind": _kind_name(int(span.get("kind", 0))),
                        "service_name": service_name,
                        "attributes": _json_attributes(span.get("attributes", [])),
                        "scope": scope_name,
                    }
                )
    return records


def decode_export_request(payload: bytes, content_type: str = "") -> list[dict[str, Any]]:
    """Decode an OTLP trace export request into flat span records.

    Args:
        payload: Encoded ``ExportTraceServiceRequest`` body.
        content_type: HTTP content type used to choose the decoder.

    Returns:
        One dictionary per span with hex ids, name, kind, service name,
        attributes and parent span id.

    """
    if "json" in content_type.lower():
        return decode_json_export_request(payload)
    request = trace_service_pb2.ExportTraceServiceRequest()
    request.ParseFromString(payload)
    records: list[dict[str, Any]] = []
    for resource_spans in request.resource_spans:
        resource_attrs = _attributes(resource_spans.resource)
        service_name = resource_attrs.get("service.name", "unknown")
        for scope_spans in resource_spans.scope_spans:
            for span in scope_spans.spans:
                records.append(
                    {
                        "trace_id": span.trace_id.hex(),
                        "span_id": span.span_id.hex(),
                        "parent_span_id": span.parent_span_id.hex() or None,
                        "name": span.name,
                        "kind": trace_pb2.Span.SpanKind.Name(span.kind),
                        "service_name": service_name,
                        "attributes": _attributes(span),
                        "scope": scope_spans.scope.name,
                    }
                )
    return records


def read_body(handler: BaseHTTPRequestHandler) -> bytes:
    """Read an HTTP request body with or without chunked encoding.

    Args:
        handler: The active request handler.

    Returns:
        The complete request body as bytes.

    """
    transfer_encoding = handler.headers.get("Transfer-Encoding", "").lower()
    if "chunked" not in transfer_encoding:
        length = int(handler.headers.get("Content-Length", "0"))
        return handler.rfile.read(length)

    parts: list[bytes] = []
    while True:
        size_line = handler.rfile.readline().strip()
        size = int(size_line.split(b";", 1)[0], 16)
        if size == 0:
            while handler.rfile.readline().strip():
                pass
            break
        parts.append(handler.rfile.read(size))
        handler.rfile.read(2)
    return b"".join(parts)


class TraceHandler(BaseHTTPRequestHandler):
    """HTTP handler accepting OTLP trace payloads on the loopback interface."""

    output_path: str = "artifacts/spans.jsonl"

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        """Decode and append a trace export request, then return 200."""
        payload = read_body(self)
        if self.path.rstrip("/") != "/v1/traces":
            self.send_error(404)
            return
        try:
            records = decode_export_request(payload, self.headers.get("Content-Type", ""))
        except Exception as exc:  # noqa: BLE001 - receiver must not drop the exporter
            self.send_error(400, f"invalid OTLP payload: {exc}")
            return
        os.makedirs(os.path.dirname(self.output_path) or ".", exist_ok=True)
        with open(self.output_path, "a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        """Expose a simple health probe used by the spike runner."""
        if self.path.rstrip("/") == "/health":
            body = b'{"status":"ok"}\n'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def log_message(self, fmt: str, *args: Any) -> None:
        """Suppress per-request access logs; artifacts carry the evidence."""
        return


def parse_args() -> argparse.Namespace:
    """Parse receiver command-line options.

    Returns:
        Parsed arguments containing host, port and output path.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--output", default=TraceHandler.output_path)
    return parser.parse_args()


def main() -> None:
    """Start the loopback OTLP receiver until interrupted."""
    args = parse_args()
    TraceHandler.output_path = args.output
    server = ThreadingHTTPServer((args.host, args.port), TraceHandler)
    print(f"OTLP receiver listening on http://{args.host}:{args.port}/v1/traces", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
