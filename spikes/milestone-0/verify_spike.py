#!/usr/bin/env python3
"""Verify Milestone 0 spike artifacts against the exit criteria.

The script checks that Pi executed a tool, observed streaming updates, and that
the same W3C trace id appears in the runtime span, the Marga span and the
headers Marga sent to the backend.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

TRACE_PARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def _read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object from disk.

    Args:
        path: File path.

    Returns:
        Parsed JSON object.

    Raises:
        ValueError: When the file does not contain an object.

    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSON-lines artifact.

    Args:
        path: File path.

    Returns:
        List of decoded objects.

    """
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _trace_ids_from_headers(records: list[dict[str, Any]]) -> set[str]:
    """Extract trace ids from captured W3C traceparent headers.

    Args:
        records: Captured header records.

    Returns:
        Set of trace ids.

    """
    trace_ids: set[str] = set()
    for record in records:
        value = record.get("traceparent")
        if not isinstance(value, str):
            continue
        match = TRACE_PARENT_RE.match(value)
        if match is not None:
            trace_ids.add(match.group(1))
    return trace_ids


def verify(artifact_dir: Path) -> dict[str, Any]:
    """Check all Milestone 0 spike artifacts.

    Args:
        artifact_dir: Directory containing spike artifacts.

    Returns:
        Structured report including the shared trace id.

    Raises:
        AssertionError: When an exit criterion is not met.

    """
    result = _read_json(artifact_dir / "pi-result.json")
    spans = _read_jsonl(artifact_dir / "spans.jsonl")
    marga_headers = _read_jsonl(artifact_dir / "marga-headers.jsonl")
    mock_headers = _read_jsonl(artifact_dir / "mock-headers.jsonl")

    runtime_spans = [span for span in spans if span.get("service_name") == "karta-runtime-spike"]
    marga_spans = [span for span in spans if span.get("service_name") == "karta-marga-spike"]
    assert runtime_spans, "OpenLIT did not export any runtime span"
    assert marga_spans, "OpenLIT did not export any Marga span"

    runtime_trace_ids = {span["trace_id"] for span in runtime_spans}
    marga_trace_ids = {span["trace_id"] for span in marga_spans}
    shared = runtime_trace_ids & marga_trace_ids
    assert shared, (
        "No shared trace id between runtime and Marga spans: "
        f"{runtime_trace_ids} vs {marga_trace_ids}"
    )
    trace_id = sorted(shared)[0]

    assert _trace_ids_from_headers(marga_headers) == {trace_id}, (
        "Marga did not receive the runtime's traceparent unchanged"
    )
    assert _trace_ids_from_headers(mock_headers) == {trace_id}, (
        "Marga did not propagate the trace context to its backend"
    )

    assert "4" in str(result.get("text", "")), f"Final answer missing: {result.get('text')!r}"
    assert "add" in result.get("executedTools", []), "The Pi loop did not execute the add tool"
    assert int(result.get("streamingDeltaCount", 0)) > 1, "No streaming text deltas were observed"
    event_types = {event.get("eventType") for event in result.get("events", [])}
    assert "tool_execution_end" in event_types, "No tool execution event was emitted"
    assert "message_update" in event_types, "No message update event was emitted"

    return {
        "status": "pass",
        "trace_id": trace_id,
        "runtime_span_count": len(runtime_spans),
        "marga_span_count": len(marga_spans),
        "streaming_delta_count": result["streamingDeltaCount"],
        "executed_tools": result["executedTools"],
        "final_text": result["text"],
    }


def parse_args() -> argparse.Namespace:
    """Parse verification options.

    Returns:
        Parsed arguments containing the artifact directory.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", default="artifacts")
    return parser.parse_args()


def main() -> None:
    """Verify artifacts and write the verification report."""
    args = parse_args()
    report = verify(Path(args.artifact_dir))
    output = Path(args.artifact_dir) / "verification.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
