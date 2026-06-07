#!/usr/bin/env python3
"""Smoke: catalog sync diff + auto-ingest idempotency (ADR-0046)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.body.catalog_ingest import run_catalog_auto_ingest
from casa.body.contracts import FunctionSpec
from casa.body.extension import parse_function_spec


def _stub_catalog_v1() -> dict[str, FunctionSpec]:
    rows = [
        {
            "function_id": "tool.git.status",
            "title": "Git status",
            "description": "Working tree status in workspace repository",
            "input_schema": {"type": "object", "properties": {}},
            "backend_id": "stub",
            "wire": {"kind": "mcp", "server": "cascade-ide", "tool": "ide_git_status"},
        },
        {
            "function_id": "tool.notes.read",
            "title": "Read agent notes",
            "description": "Read session notes from agent-notes file",
            "input_schema": {"type": "object", "properties": {}},
            "backend_id": "stub",
            "wire": {"kind": "mcp", "server": "cascade-ide", "tool": "ide_read_agent_notes"},
        },
    ]
    return {r["function_id"]: parse_function_spec(r) for r in rows}


def _stub_catalog_v2(catalog: dict[str, FunctionSpec]) -> dict[str, FunctionSpec]:
    out = dict(catalog)
    out["tool.build.verify"] = FunctionSpec(
        function_id="tool.build.verify",
        title="Verify build",
        description="Run verification ladder on current solution",
        input_schema={
            "type": "object",
            "properties": {"policy": {"type": "string"}},
        },
        backend_id="stub",
        wire={"kind": "ide_command", "command_id": "ide_agent_verify"},
    )
    changed = out["tool.git.status"]
    out["tool.git.status"] = FunctionSpec(
        function_id=changed.function_id,
        title=changed.title,
        description=changed.description + " (updated)",
        input_schema=changed.input_schema,
        backend_id=changed.backend_id,
        wire=dict(changed.wire),
    )
    return out


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="casa-body-catalog-"))
    try:
        v1 = _stub_catalog_v1()
        r1 = run_catalog_auto_ingest(tmp, v1, persist_manifest=True)
        r2 = run_catalog_auto_ingest(
            tmp,
            v1,
            last_digest=r1.new_digest,
            persist_manifest=True,
        )
        v2 = _stub_catalog_v2(v1)
        r3 = run_catalog_auto_ingest(
            tmp,
            v2,
            last_digest=r2.new_digest,
            persist_manifest=True,
        )

        ok = (
            r1.event_count == 2
            and r1.added == 2
            and r2.skipped
            and r2.event_count == 0
            and r3.event_count == 2
            and r3.added == 1
            and r3.changed == 1
            and all(ev.get("body", {}).get("kind") == "tool_catalog" for ev in r1.events)
        )
        sample = r1.events[0] if r1.events else {}
        report = {
            "ok": ok,
            "store": str(tmp),
            "run1": r1.to_dict(),
            "run2_idempotent": r2.to_dict(),
            "run3_diff": r3.to_dict(),
            "sample_mm_event": sample,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
