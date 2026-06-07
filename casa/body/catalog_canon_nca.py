#!/usr/bin/env python3
"""Default body_manifest entries for canon NCA worker (ADR-0046)."""

from __future__ import annotations

from typing import Any

from casa.body.handlers.canon_nca import FUNCTION_ID


def canon_nca_function_spec() -> dict[str, Any]:
    return {
        "function_id": FUNCTION_ID,
        "title": "Train canon NCA queue",
        "description": (
            "Drain pending immutable-lattice NCA jobs. Runs outside agent tick/sleep "
            "so training can proceed in parallel with agent life."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_jobs": {"type": "integer", "minimum": 1, "default": 1},
                "device": {"type": "string", "default": "cpu"},
            },
        },
        "backend_id": "in_process",
        "wire": {"kind": "in_process", "handler": FUNCTION_ID},
    }


def merge_canon_nca_into_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Idempotently add canon NCA function + in_process backend to a manifest copy."""
    out = dict(manifest)
    backends = dict(out.get("backends") or {})
    if "in_process" not in backends:
        backends["in_process"] = {}
    out["backends"] = backends

    functions: list[dict[str, Any]] = [
        dict(f) for f in (out.get("functions") or []) if isinstance(f, dict)
    ]
    spec = canon_nca_function_spec()
    functions = [f for f in functions if f.get("function_id") != spec["function_id"]]
    functions.append(spec)
    out["functions"] = functions
    return out
