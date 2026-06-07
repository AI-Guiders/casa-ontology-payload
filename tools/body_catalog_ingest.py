#!/usr/bin/env python3
"""CLI: sync tool catalog into store manifest + tool_catalog.live.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.body.catalog_ingest import run_catalog_auto_ingest
from casa.body.catalog_sync import specs_from_mcp_tools, parse_incoming_specs
from casa.body.extension import load_body_manifest, specs_from_manifest


def main() -> int:
    p = argparse.ArgumentParser(description="Auto-ingest tool catalog diff (ADR-0046)")
    p.add_argument("--store-dir", type=Path, default=Path("agents/von-neumann"))
    p.add_argument(
        "--from-manifest",
        action="store_true",
        help="Re-ingest from existing body_manifest.functions (lab replay)",
    )
    p.add_argument(
        "--mcp-tools-json",
        type=Path,
        default=None,
        help="JSON file: {server_id, tools: [...]} from tools/list capture",
    )
    p.add_argument("--dry-run", action="store_true", help="Do not write manifest/jsonl")
    args = p.parse_args()

    store = args.store_dir.resolve()
    manifest = load_body_manifest(store)

    if args.mcp_tools_json:
        payload = json.loads(args.mcp_tools_json.read_text(encoding="utf-8"))
        server_id = str(payload.get("server_id") or "unknown")
        tools = payload.get("tools") if isinstance(payload.get("tools"), list) else []
        incoming = specs_from_mcp_tools(tools, server_id=server_id)
    elif args.from_manifest:
        incoming = specs_from_manifest(manifest)
    else:
        example = store / "body_manifest.example.json"
        if example.is_file():
            incoming = specs_from_manifest(json.loads(example.read_text(encoding="utf-8")))
        else:
            print("No --mcp-tools-json and no body_manifest.example.json", file=sys.stderr)
            return 2

    report = run_catalog_auto_ingest(
        store,
        incoming,
        persist_manifest=not args.dry_run,
        append_jsonl=not args.dry_run,
    )
    out = report.to_dict()
    if args.dry_run:
        out["events_preview"] = report.events[:3]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
