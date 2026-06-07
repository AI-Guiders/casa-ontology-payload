#!/usr/bin/env python3
"""Smoke test for body function extension (no MCP/CIDE required)."""

from __future__ import annotations

import json
from pathlib import Path

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.body.contracts import FunctionCallIntent
from casa.body.extension import BodyFunctionExtension
from casa.body.mm_bridge import function_result_to_mm_event


def main() -> int:
    manifest = {
        "schema_version": 1,
        "body_profile_id": "smoke",
        "default_backend": "stub",
        "backends": {"stub": {}},
        "functions": [
            {
                "function_id": "tool.echo.ping",
                "title": "Echo ping",
                "description": "Stub echo for smoke",
                "input_schema": {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                },
                "backend_id": "stub",
                "wire": {"kind": "stub", "tool": "echo_ping"},
            }
        ],
    }
    ext = BodyFunctionExtension(Path("."), manifest=manifest)  # type: ignore[name-defined]
    intent = FunctionCallIntent(
        function_id="tool.echo.ping",
        arguments={"message": "body extension ok"},
        call_id="smoke-1",
        provenance={"source": "casa.body.smoke"},
    )
    result = ext.dispatch(intent)
    event = function_result_to_mm_event(intent, result)
    report = {
        "ok": result.ok,
        "health": ext.health(),
        "result": {
            "summary": result.summary,
            "wire_backend": result.wire_backend,
        },
        "mm_event": event,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
