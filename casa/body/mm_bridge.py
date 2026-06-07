#!/usr/bin/env python3
"""Bridge function call results into mm_event-shaped percepts (ADR-0026 / 0046)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from casa.body.contracts import FunctionCallIntent, FunctionCallResult


def function_result_to_mm_event(
    intent: FunctionCallIntent,
    result: FunctionCallResult,
    *,
    window_ms: int = 0,
) -> dict[str, Any]:
    """Compress wire tool output for ingest — not full MCP payload."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tags = ["body:function_call", f"fn:{result.function_id}", "ok" if result.ok else "error"]
    if result.error_code:
        tags.append(f"err:{result.error_code}")

    words = [w for w in result.summary.split() if w][:24]
    return {
        "schema": "mm_event_v1",
        "at": ts,
        "window_ms": window_ms,
        "source": "body_extension",
        "canon": {
            "words": words,
            "context": tags,
        },
        "body": {
            "kind": "function_call",
            "call_id": result.call_id,
            "function_id": result.function_id,
            "ok": result.ok,
            "summary": result.summary,
            "structured_keys": sorted((result.structured or {}).keys()),
            "error_code": result.error_code,
            "wire_backend": result.wire_backend,
            "duration_ms": result.duration_ms,
            "provenance": intent.provenance,
        },
    }
