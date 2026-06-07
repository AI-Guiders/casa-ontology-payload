#!/usr/bin/env python3
"""Merge agent pending_world_claims → KB bundle agent.world.* (ADR-0054)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_DEFAULT_BUNDLE = _REPO / "agents/von-neumann/bundles/kb-agent-world-v1.bundle.json"


def _normalize_claim(raw: dict[str, Any]) -> dict[str, Any] | None:
    cid = str(raw.get("concept_id") or "")
    if not cid.startswith("agent.world."):
        return None
    claim: dict[str, Any] = {"concept_id": cid, "slots": dict(raw.get("slots") or {})}
    for key in ("text", "section", "doc_path", "relation", "src", "dst"):
        if raw.get(key):
            claim[key] = raw[key]
    return claim


def compile_pending_claims(
    pending: list[dict[str, Any]],
    bundle_path: Path,
    *,
    clear_manifest_pending: Path | None = None,
) -> dict[str, Any]:
    if bundle_path.is_file():
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    else:
        bundle = {
            "schema_version": 1,
            "bundle_id": "kb-agent-world-v1",
            "title": "Agent world model v1 (RU-ε)",
            "claims": [],
        }
    by_id = {str(c.get("concept_id") or ""): c for c in bundle.get("claims") or [] if c.get("concept_id")}
    merged = 0
    for raw in pending:
        claim = _normalize_claim(raw)
        if not claim:
            continue
        by_id[str(claim["concept_id"])] = claim
        merged += 1
    bundle["claims"] = list(by_id.values())
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if clear_manifest_pending is not None and clear_manifest_pending.is_file():
        manifest = json.loads(clear_manifest_pending.read_text(encoding="utf-8"))
        manifest["pending_world_claims"] = []
        clear_manifest_pending.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "out": str(bundle_path),
        "merged": merged,
        "claims_total": len(bundle["claims"]),
        "cleared_manifest": str(clear_manifest_pending) if clear_manifest_pending else None,
    }


def load_pending_from_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    if not manifest_path.is_file():
        return []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return list(data.get("pending_world_claims") or [])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=None, help="Agent manifest with pending_world_claims")
    p.add_argument("--bundle", type=Path, default=_DEFAULT_BUNDLE)
    p.add_argument("--clear-manifest", action="store_true")
    args = p.parse_args()

    manifest = args.manifest or (_REPO / "agents/von-neumann/memory_manifest.json")
    pending = load_pending_from_manifest(manifest)
    clear = manifest if args.clear_manifest else None
    result = compile_pending_claims(pending, args.bundle, clear_manifest_pending=clear)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
