#!/usr/bin/env python3
"""Body completion percepts — sensory ingress; agent owns checkpoint commit (ADR-0046)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.body.contracts import FunctionCallIntent
from casa.body.mm_bridge import function_result_to_mm_event


def body_completions_path(store_dir: Path) -> Path:
    return store_dir.resolve() / "body" / "completions.jsonl"


def append_body_completion_percept(
    store_dir: Path,
    *,
    function_id: str,
    ok: bool,
    summary: str,
    structured: dict[str, Any] | None = None,
    call_id: str = "",
    provenance: dict[str, Any] | None = None,
    error_code: str | None = None,
) -> dict[str, Any]:
    """Append mm_event-shaped row for agent ingest — tools do not write field_state."""
    from casa.body.contracts import FunctionCallResult

    intent = FunctionCallIntent(
        function_id=function_id,
        arguments={},
        call_id=call_id or "body-completion",
        provenance={"source": "body_worker", **(provenance or {})},
    )
    result = FunctionCallResult(
        call_id=intent.call_id,
        function_id=function_id,
        ok=ok,
        summary=summary,
        structured=structured,
        error_code=error_code,
        wire_backend="in_process",
    )
    event = function_result_to_mm_event(intent, result)
    if structured:
        body = event.setdefault("body", {})
        if isinstance(body, dict):
            body["structured"] = structured
    path = body_completions_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event
